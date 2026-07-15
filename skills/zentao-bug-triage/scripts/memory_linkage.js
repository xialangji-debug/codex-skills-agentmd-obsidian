"use strict";

const fs = require("fs");
const path = require("path");

const DOMAIN_TERMS = [
  "云相册", "联系人", "白名单", "通讯录", "微聊", "微信支付", "扫码", "定位", "gps",
  "课堂模式", "免打扰", "闹钟", "计步", "工模", "老化", "开关机", "低电", "sim",
  "短信", "消息", "协议", "上报", "下发", "小程序", "app", "ui", "lvgl", "相机",
  "摄像头", "录音", "喇叭", "马达", "振动", "充电", "功耗", "dump", "crash",
];

const GENERIC_TERMS = new Set([
  "问题", "错误", "失败", "异常", "功能", "设备", "手表", "当前", "显示", "需要", "无法",
  "出现", "测试", "复测", "结果", "期望", "步骤", "修改", "修复", "版本", "项目", "代码",
]);

function normalize(value) {
  return `${value || ""}`.toLowerCase().replace(/\\/g, "/").replace(/\s+/g, " ").trim();
}

function unique(values) {
  return Array.from(new Set(values.filter(Boolean)));
}

function readSection(markdown, names) {
  const escaped = names.map((name) => name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
  const match = markdown.match(new RegExp(`^##\\s+(?:${escaped})\\s*$([\\s\\S]*?)(?=^##\\s+|(?![\\s\\S]))`, "im"));
  return match ? match[1].trim() : "";
}

function extractTerms(value) {
  const text = normalize(value);
  const latin = text.match(/[a-z_][a-z0-9_.\/-]{2,}/g) || [];
  const chineseRuns = text.match(/[\u4e00-\u9fff]{2,}/g) || [];
  const chinese = [];
  for (const run of chineseRuns) {
    if (run.length <= 8) chinese.push(run);
    for (let size = 2; size <= Math.min(4, run.length); size++) {
      for (let i = 0; i <= run.length - size; i++) chinese.push(run.slice(i, i + size));
    }
  }
  return unique([...latin, ...chinese]).filter((term) => !GENERIC_TERMS.has(term));
}

function extractExplicitKeywords(markdown) {
  const section = readSection(markdown, ["Keywords", "关键词", "关键字"]);
  if (!section) return [];
  return unique(section
    .replace(/^[-*]\s*/gm, "")
    .split(/[、,，;；|\n]/)
    .map((term) => normalize(term).replace(/^`|`$/g, ""))
    .filter((term) => term.length >= 2));
}

function detectVerification(markdown) {
  const text = normalize([
    readSection(markdown, ["Verification", "验证", "验证结果"]),
    markdown.match(/(?:验证状态|验证结果|用户确认)\s*[:：].*/gi)?.join("\n") || "",
  ].join("\n"));
  if (/未验证|待验证|待真机|待回归|未回归|失败|不通过/.test(text)) return "unverified";
  if (/已验证|验证通过|已通过|用户确认|回归通过|真机通过|verified|passed/.test(text)) return "verified";
  return "unknown";
}

function parseNote(filePath, root) {
  const markdown = fs.readFileSync(filePath, "utf8");
  const title = (markdown.match(/^#\s+(.+)$/m) || [])[1]?.trim() || path.basename(filePath, ".md");
  const applicable = readSection(markdown, ["Applicable", "适用范围", "适用项目", "项目与版本"]);
  const symptoms = readSection(markdown, ["Symptoms", "症状", "现象"]);
  const keyFiles = readSection(markdown, ["Key Files", "关键文件", "相关文件"]);
  const keywords = extractExplicitKeywords(markdown);
  return {
    title,
    path: filePath,
    relativePath: path.relative(root, filePath).replace(/\\/g, "/"),
    verification: detectVerification(markdown),
    applicable: normalize(applicable),
    keywords,
    terms: unique(extractTerms(`${title}\n${keywords.join("\n")}\n${symptoms}`)),
    codeTokens: unique((`${keyFiles}\n${markdown}`.match(/[A-Za-z_][A-Za-z0-9_]{3,}/g) || []).map(normalize)),
    searchable: normalize(`${title}\n${keywords.join("\n")}\n${applicable}\n${symptoms}\n${keyFiles}`),
  };
}

function listMarkdownFiles(root) {
  if (!root || !fs.existsSync(root)) return [];
  const files = [];
  const visit = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) visit(fullPath);
      else if (entry.isFile() && entry.name.toLowerCase().endsWith(".md")) files.push(fullPath);
    }
  };
  visit(root);
  return files.sort();
}

function loadMemoryIndex(root) {
  const errors = [];
  const notes = [];
  for (const filePath of listMarkdownFiles(root)) {
    try {
      notes.push(parseNote(filePath, root));
    } catch (error) {
      errors.push({ path: filePath, error: error.message });
    }
  }
  return { root, notes, errors };
}

function buildBugFingerprint(bug) {
  const text = normalize([
    bug.title, bug.steps, bug.actual, bug.expected, bug.product,
    bug.lastActivation?.note, bug.lastActivation?.actual, bug.lastActivation?.expected,
  ].join("\n"));
  const codeTokens = unique((text.match(/[a-z_][a-z0-9_]{3,}/g) || [])
    .filter((term) => /_|event|msg|handler|callback|lv_|lvgl|gps|sim|nv_|task|func|camera|album/.test(term)));
  const domainTerms = DOMAIN_TERMS.filter((term) => text.includes(term));
  return {
    text,
    terms: extractTerms(text),
    codeTokens,
    domainTerms,
  };
}

function contextTokens(ctx) {
  return unique([
    normalize(ctx.repoName), normalize(path.basename(ctx.repo || "")), normalize(ctx.branch),
    normalize(ctx.deviceVer), normalize(ctx.deviceName), normalize(ctx.projectName),
  ]).filter((term) => term && term !== "unknown" && term.length >= 3);
}

function scoreNote(note, fingerprint, ctx) {
  let score = 0;
  const reasons = [];
  const dimensions = new Set();
  const contextMatches = contextTokens(ctx).filter((term) => note.searchable.includes(term));
  const sameProject = contextMatches.length > 0;
  if (sameProject) {
    score += contextMatches.some((term) => term === normalize(ctx.branch)) ? 5 : 3;
    reasons.push(`项目/分支匹配：${contextMatches.slice(0, 2).join("、")}`);
    dimensions.add("project");
  }

  const keywordHits = note.keywords.filter((term) => fingerprint.text.includes(term));
  if (keywordHits.length) {
    score += Math.min(6, keywordHits.length * 2);
    reasons.push(`关键词：${keywordHits.slice(0, 4).join("、")}`);
    dimensions.add("keyword");
  }

  const codeHits = note.codeTokens.filter((term) => fingerprint.codeTokens.includes(term));
  if (codeHits.length) {
    score += Math.min(6, codeHits.length * 2);
    reasons.push(`代码标识：${codeHits.slice(0, 3).join("、")}`);
    dimensions.add("code");
  }

  const domainHits = fingerprint.domainTerms.filter((term) => note.searchable.includes(term));
  if (domainHits.length) {
    score += Math.min(4, domainHits.length * 2);
    reasons.push(`业务域：${domainHits.slice(0, 3).join("、")}`);
    dimensions.add("domain");
  }

  const termHits = note.terms.filter((term) => term.length >= 3 && fingerprint.terms.includes(term));
  if (termHits.length) {
    score += Math.min(4, termHits.length);
    reasons.push(`症状相似：${termHits.slice(0, 4).join("、")}`);
    dimensions.add("symptom");
  }

  if (note.verification === "verified") {
    score += 2;
    reasons.push("记忆已验证");
  } else if (note.verification === "unverified") {
    score -= 1;
    reasons.push("记忆尚未验证");
  }

  const issueDimensions = Array.from(dimensions).filter((name) => name !== "project").length;
  const strongIssueEvidence = keywordHits.length > 0 || codeHits.length > 0 || domainHits.length > 0 || termHits.length >= 2;
  return { score: Math.max(0, score), reasons, dimensions: dimensions.size, issueDimensions, strongIssueEvidence, sameProject, codeHits };
}

function matchBugToMemory(bug, notes, ctx) {
  const fingerprint = buildBugFingerprint(bug);
  const candidates = notes.map((note) => {
    const scored = scoreNote(note, fingerprint, ctx);
    return {
      title: note.title,
      path: note.path,
      relativePath: note.relativePath,
      score: scored.score,
      verified: note.verification === "verified",
      verification: note.verification,
      sameProject: scored.sameProject,
      evidenceDimensions: scored.dimensions,
      issueEvidenceDimensions: scored.issueDimensions,
      strongIssueEvidence: scored.strongIssueEvidence,
      codeHits: scored.codeHits,
      reasons: scored.reasons,
    };
  }).filter((item) => item.score >= 3 && item.strongIssueEvidence)
    .sort((a, b) => b.score - a.score || Number(b.verified) - Number(a.verified))
    .slice(0, 3);

  const top = candidates[0];
  let level = "未命中";
  if (top) {
    if (top.score >= 10 && top.verified && top.evidenceDimensions >= 2 && (top.sameProject || top.codeHits.length)) level = "高";
    else if (top.score >= 6) level = "中";
    else level = "低";
  }
  return {
    fingerprint,
    match: {
      level,
      score: top?.score || 0,
      reasons: top?.reasons || [],
      candidates,
    },
  };
}

function evidenceExists(bug) {
  return [...(bug.attachmentLinks || []), ...(bug.attachments || [])].length > 0;
}

function expectationIsClear(bug) {
  const text = normalize(`${bug.expected || ""}\n${bug.lastActivation?.expected || ""}`);
  return text.length >= 4 || /应该|需要|改成|换成|去掉|不能|显示为|提示/.test(`${bug.title || ""}\n${bug.steps || ""}`);
}

function assessRepairEligibility(bug) {
  const checks = ["核对当前分支实现", "检查 git 历史/现有改动", "按 bug 复现步骤验证"];
  const status = normalize(bug.status);
  const memory = bug.memoryMatch || { level: "未命中", candidates: [] };
  const top = memory.candidates?.[0];

  if (/已解决|已关闭|resolved|closed/.test(status)) {
    return { label: "本轮不处理", directCandidate: false, reason: "禅道状态已解决或已关闭。", requiredChecks: [] };
  }
  if (bug.category === "平台端" || /不直接处理-平台/.test(bug.canHandle || "")) {
    return { label: "非固件问题", directCandidate: false, reason: "当前证据更偏平台、后台或账号配置。", requiredChecks: ["补平台请求/响应或后台配置证据"] };
  }
  if (bug.category === "底层/硬件/驱动" || /不直接处理-底层/.test(bug.canHandle || "")) {
    return { label: "需底层/硬件处理", directCandidate: false, reason: "需要驱动、硬件、功耗或崩溃证据。", requiredChecks: ["补 CATStudio/dump/硬件版本证据"] };
  }
  if (!bug.detailFetched) {
    return { label: "需先深抓", directCandidate: false, reason: "当前只有列表摘要，不能据此直接改代码。", requiredChecks: ["用 --ids 深抓完整详情和附件"] };
  }
  if (bug.reactivated) {
    return { label: "复测激活-需重新定位", directCandidate: false, reason: "历史修复已被复测否定，必须以后续激活说明重新定位。", requiredChecks: checks };
  }
  if (bug.logsNeeded && !evidenceExists(bug)) {
    return { label: "需日志验证", directCandidate: false, reason: "协议、时序或偶现问题缺关键日志/附件。", requiredChecks: ["补协议包、CATStudio 日志或复现视频"] };
  }
  if (bug.handlingBucket === "work" && memory.level === "高" && top?.verified && top.sameProject && expectationIsClear(bug)) {
    return {
      label: "可直接修复候选",
      directCandidate: true,
      reason: "同项目已验证记忆高度命中，且当前 bug 期望明确；仍需通过当前代码和 Git 检查后才能修改。",
      requiredChecks: checks,
    };
  }
  if (bug.handlingBucket === "work" && ["高", "中"].includes(memory.level)) {
    return { label: "可移植候选", directCandidate: false, reason: "存在相似修复记忆，但项目、分支或证据不足以直接套用。", requiredChecks: checks };
  }
  if (bug.handlingBucket === "work") {
    return { label: "需先查代码", directCandidate: false, reason: "可以进入代码排查，但没有足够可靠的已验证记忆。", requiredChecks: checks };
  }
  return { label: "需确认信息", directCandidate: false, reason: bug.handlingReason || "现有信息不足。", requiredChecks: [] };
}

function enrichBugsWithMemory(bugs, ctx, options = {}) {
  const enabled = options.enabled !== false;
  const root = options.root || "";
  const index = enabled ? loadMemoryIndex(root) : { root, notes: [], errors: [] };
  const enriched = bugs.map((bug) => {
    const result = enabled ? matchBugToMemory(bug, index.notes, ctx) : {
      fingerprint: buildBugFingerprint(bug),
      match: { level: "未启用", score: 0, reasons: [], candidates: [] },
    };
    const withMemory = { ...bug, bugFingerprint: result.fingerprint, memoryMatch: result.match };
    return { ...withMemory, repairEligibility: assessRepairEligibility(withMemory) };
  });
  const counts = {};
  for (const bug of enriched) counts[bug.memoryMatch.level] = (counts[bug.memoryMatch.level] || 0) + 1;
  return {
    bugs: enriched,
    summary: {
      enabled,
      root,
      indexedNotes: index.notes.length,
      indexErrors: index.errors,
      counts,
      directCandidates: enriched.filter((bug) => bug.repairEligibility.directCandidate).length,
    },
  };
}

module.exports = {
  assessRepairEligibility,
  buildBugFingerprint,
  enrichBugsWithMemory,
  loadMemoryIndex,
  matchBugToMemory,
};
