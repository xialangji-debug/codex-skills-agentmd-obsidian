#!/usr/bin/env node
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const cp = require("child_process");

const SITE_URL = "http://zentao.hzyuelan.com/zentao";
const PROJECT_CACHE_PATH = path.join(os.homedir(), ".codex", "zentao-bug-triage", "project-cache.json");

function parseArgs(argv) {
  const args = {
    repo: process.cwd(),
    assigned: false,
    assignedTo: "",
    assignedScanLimit: 500,
    currentProject: true,
    limit: 80,
    detailLimit: -1,
    detailConcurrency: 4,
    detailRetries: 2,
    detailTimeoutMs: 60000,
    downloadMode: "all",
    headed: false,
    projectName: "",
    projectKey: "",
    projectId: "",
    productId: "",
    bugStatus: "all",
    ids: [],
    output: "",
    expectRepoName: "",
    expectBranch: "",
    writeObsidian: false,
    workMd: true,
    cleanup: "",
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    const next = () => {
      if (i + 1 >= argv.length) throw new Error(`Missing value for ${a}`);
      return argv[++i];
    };
    if (a === "--repo") args.repo = next();
    else if (a === "--assigned") args.assigned = true;
    else if (a === "--assigned-to") args.assignedTo = next();
    else if (a === "--mine") args.assignedTo = "me";
    else if (a === "--current-mine-active") {
      args.currentProject = true;
      args.assignedTo = "me";
      args.bugStatus = "active";
    }
    else if (a === "--assigned-scan-limit") args.assignedScanLimit = Number(next());
    else if (a === "--active-only") args.bugStatus = "active";
    else if (a === "--current-project") args.currentProject = true;
    else if (a === "--no-current-project") args.currentProject = false;
    else if (a === "--limit") args.limit = Number(next());
    else if (a === "--detail-limit") args.detailLimit = Number(next());
    else if (a === "--detail-concurrency") args.detailConcurrency = Number(next());
    else if (a === "--detail-retries") args.detailRetries = Number(next());
    else if (a === "--detail-timeout-ms") args.detailTimeoutMs = Number(next());
    else if (a === "--download-attachments") args.downloadMode = "all";
    else if (a === "--no-download-attachments") args.downloadMode = "none";
    else if (a === "--headed") args.headed = true;
    else if (a === "--project-name") args.projectName = next();
    else if (a === "--project-key") args.projectKey = next();
    else if (a === "--project-id") args.projectId = next();
    else if (a === "--product-id") args.productId = next();
    else if (a === "--bug-status") args.bugStatus = next();
    else if (a === "--ids") args.ids = next().split(/[,\s]+/).filter(Boolean);
    else if (a === "--output") args.output = next();
    else if (a === "--expect-repo-name") args.expectRepoName = next();
    else if (a === "--expect-branch") args.expectBranch = next();
    else if (a === "--write-obsidian") args.writeObsidian = true;
    else if (a === "--write-work-md") args.workMd = true;
    else if (a === "--no-work-md") args.workMd = false;
    else if (a === "--cleanup") args.cleanup = next();
    else if (a === "--help" || a === "-h") {
      console.log(`Usage:
  node zentao_bug_snapshot.js --repo . --limit 80
  node zentao_bug_snapshot.js --repo . --limit 80 --detail-concurrency 4
  node zentao_bug_snapshot.js --repo . --limit 80 --detail-limit 20 --detail-concurrency 4
  node zentao_bug_snapshot.js --repo . --limit 80 --detail-retries 2 --detail-timeout-ms 60000
  node zentao_bug_snapshot.js --repo . --current-mine-active --limit 80
  node zentao_bug_snapshot.js --repo . --assigned --limit 80 [--download-attachments]
  node zentao_bug_snapshot.js --repo . --assigned-to me --bug-status active --limit 80
  node zentao_bug_snapshot.js --repo . --project-name "TW18_阿科奇_LT52_乐智" --limit 80
  node zentao_bug_snapshot.js --repo . --project-id 134 --limit 80
  node zentao_bug_snapshot.js --repo . --product-id 42 --project-name "TW18_阿科奇_LT52_APP" --limit 80
  node zentao_bug_snapshot.js --repo . --bug-status unresolved --detail-limit 0
  node zentao_bug_snapshot.js --repo . --ids 2947,2906,2894 --download-attachments
  node zentao_bug_snapshot.js --repo . --expect-repo-name lt52_XCX_GB --expect-branch TW18_LT52_3602_小程序协议腕表20251218 --current-mine-active
  node zentao_bug_snapshot.js --cleanup "C:\\Users\\...\\.codex\\zentao-bug-triage\\snapshots\\<snapshot>"

Defaults:
  With only --repo, the script reads references/project-map.md, resolves the current
  branch/yl_device_ver to a Zentao project, and fetches that project. If no exact
  project mapping is found it falls back to --assigned.
  --expect-repo-name and --expect-branch are preflight guards. When provided, any
  mismatch aborts before opening Zentao, which prevents fetching bugs from the
  wrong worktree or branch.
  By default every fetched list row opens its detail page and downloads all
  attachments. Detail pages are fetched with four parallel workers. Use
  --detail-limit 0 or --no-download-attachments only for an explicitly requested
  fast list.
  Each snapshot writes triage.md, work-items.md, and ignored-items.md unless
  --no-work-md is passed. work-items.md contains bugs Codex should inspect/fix.
  ignored-items.md contains platform/low-level/log-needed/unclear issues to skip.
  --cleanup deletes only work-items.md, ignored-items.md, and attachments/.
`);
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${a}`);
    }
  }
  return args;
}

function run(cmd, cwd) {
  try {
    return cp.execFileSync(cmd[0], cmd.slice(1), { cwd, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
  } catch {
    return "";
  }
}

function repoContext(repo) {
  const repoInput = path.resolve(repo);
  const gitRoot = run(["git", "rev-parse", "--show-toplevel"], repoInput);
  const repoRoot = path.resolve(gitRoot || repoInput);
  let branch = run(["git", "branch", "--show-current"], repoRoot);
  if (!branch) {
    branch = run(["git", "name-rev", "--name-only", "HEAD"], repoRoot)
      .replace(/^remotes\/origin\//, "")
      .replace(/~\d+$/, "");
  }
  if (!branch || branch === "undefined" || branch === "HEAD") branch = "unknown";
  const commit = run(["git", "rev-parse", "--short", "HEAD"], repoRoot) || "unknown";
  const dirty = run(["git", "status", "--short"], repoRoot);
  let deviceVer = "";
  const ylPath = path.join(repoRoot, "gui", "lv_watch", "lv_apps", "yl", "yl.h");
  if (fs.existsSync(ylPath)) {
    const text = fs.readFileSync(ylPath, "utf8");
    const m = text.match(/yl_device_ver\s+"([^"]+)"/);
    if (m) deviceVer = m[1];
  }
  let deviceName = "";
  let hwVer = "";
  let softVer = "";
  if (fs.existsSync(ylPath)) {
    const text = fs.readFileSync(ylPath, "utf8");
    const nameMatch = text.match(/yl_device_name\s+"([^"]+)"/);
    const hwMatch = text.match(/yl_hw_ver\s+"([^"]+)"/);
    const softMatch = text.match(/yl_soft_ver\s+"([^"]+)"/);
    if (nameMatch) deviceName = nameMatch[1];
    if (hwMatch) hwVer = hwMatch[1];
    if (softMatch) softVer = softMatch[1];
  }
  return { repo: repoRoot, repoInput, repoName: path.basename(repoRoot), branch, commit, dirty, deviceVer, deviceName, hwVer, softVer };
}

function normalizeText(value) {
  return (value || "").toLowerCase().replace(/\s+/g, "").trim();
}

function assertExpectedContext(ctx, args) {
  const mismatches = [];
  if (args.expectRepoName && normalizeText(ctx.repoName) !== normalizeText(args.expectRepoName)) {
    mismatches.push(`repo name expected "${args.expectRepoName}", actual "${ctx.repoName}" (${ctx.repo})`);
  }
  if (args.expectBranch && normalizeText(ctx.branch) !== normalizeText(args.expectBranch)) {
    mismatches.push(`branch expected "${args.expectBranch}", actual "${ctx.branch}"`);
  }
  if (!mismatches.length) return;
  throw new Error([
    "Preflight context mismatch. Refusing to fetch Zentao bugs from the wrong worktree/branch.",
    ...mismatches.map((item) => `- ${item}`),
  ].join("\n"));
}

function splitListValue(value) {
  if (!value) return [];
  return value.split(/[,\s]+/).map((x) => x.trim()).filter(Boolean);
}

function parseProjectMap(text) {
  const mappings = [];
  let current = null;
  let section = "";

  const pushCurrent = () => {
    if (current) mappings.push(current);
  };

  for (const raw of text.split(/\r?\n/)) {
    const line = raw.replace(/\t/g, "    ");
    const trimmed = line.trim();
    const start = trimmed.match(/^- (branch_contains|local_tokens):\s*(.*)$/);
    if (start) {
      pushCurrent();
      current = {
        branchContains: [],
        localTokens: [],
        ylDeviceVerContains: [],
        zentaoNames: [],
        projectId: "",
        productId: "",
        candidate: "",
        status: "",
        verified: "",
      };
      section = start[1];
      if (start[2]) {
        const value = start[2].replace(/^["']|["']$/g, "");
        if (section === "branch_contains") current.branchContains.push(value);
        if (section === "local_tokens") current.localTokens.push(value);
      }
      continue;
    }

    if (!current) continue;
    const sectionMatch = trimmed.match(/^(branch_contains|local_tokens|yl_device_ver_contains|zentao_names):\s*(.*)$/);
    if (sectionMatch) {
      section = sectionMatch[1];
      if (sectionMatch[2]) {
        const value = sectionMatch[2].replace(/^["']|["']$/g, "");
        if (section === "branch_contains") current.branchContains.push(value);
        else if (section === "local_tokens") current.localTokens.push(value);
        else if (section === "yl_device_ver_contains") current.ylDeviceVerContains.push(value);
        else if (section === "zentao_names") current.zentaoNames.push(value);
      }
      continue;
    }

    const itemMatch = trimmed.match(/^- (.+)$/);
    if (itemMatch && section) {
      const value = itemMatch[1].replace(/^["']|["']$/g, "");
      if (section === "branch_contains") current.branchContains.push(value);
      else if (section === "local_tokens") current.localTokens.push(value);
      else if (section === "yl_device_ver_contains") current.ylDeviceVerContains.push(value);
      else if (section === "zentao_names") current.zentaoNames.push(value);
      continue;
    }

    const scalar = trimmed.match(/^(candidate|status|verified|project_id|zentao_project_id|product_id|zentao_product_id):\s*(.+)$/);
    if (scalar) {
      const key = scalar[1] === "project_id" || scalar[1] === "zentao_project_id"
        ? "projectId"
        : (scalar[1] === "product_id" || scalar[1] === "zentao_product_id" ? "productId" : scalar[1]);
      current[key] = scalar[2].replace(/^["']|["']$/g, "");
    }
  }
  pushCurrent();
  return mappings.filter((m) => m.branchContains.length || m.localTokens.length);
}

function mappingMatches(ctx, mapping, exactOnly) {
  const branch = normalizeText(ctx.branch);
  const device = normalizeText(ctx.deviceVer);
  const combined = normalizeText(`${ctx.branch} ${ctx.deviceVer} ${ctx.deviceName} ${ctx.hwVer} ${ctx.softVer}`);

  if (exactOnly) {
    const branchOk = mapping.branchContains.length > 0 &&
      mapping.branchContains.some((token) => branch.includes(normalizeText(token)));
    const deviceOk = mapping.ylDeviceVerContains.length === 0 ||
      mapping.ylDeviceVerContains.some((token) => device.includes(normalizeText(token)));
    return branchOk && deviceOk && mapping.zentaoNames.length > 0 && mapping.status !== "unconfirmed";
  }

  if (mapping.localTokens.length > 0) {
    return mapping.localTokens.every((token) => combined.includes(normalizeText(token))) &&
      mapping.zentaoNames.length === 1;
  }

  return false;
}

function resolveCurrentProject(ctx) {
  const skillRoot = path.resolve(__dirname, "..");
  const projectMapPath = path.join(skillRoot, "references", "project-map.md");
  if (!fs.existsSync(projectMapPath)) {
    return { mode: "assigned", reason: `project-map not found: ${projectMapPath}` };
  }

  const mappings = parseProjectMap(fs.readFileSync(projectMapPath, "utf8"));
  const exact = mappings.find((mapping) => mappingMatches(ctx, mapping, true));
  if (exact) {
    return {
      mode: "project",
      projectName: exact.zentaoNames[0],
      projectId: exact.projectId || "",
      productId: exact.productId || "",
      reason: "exact branch/version mapping",
      mapping: exact,
    };
  }

  const generic = mappings.filter((mapping) => mappingMatches(ctx, mapping, false));
  const uniqueNames = Array.from(new Set(generic.flatMap((mapping) => mapping.zentaoNames)));
  if (uniqueNames.length === 1) {
    return {
      mode: "project",
      projectName: uniqueNames[0],
      projectId: generic[0]?.projectId || "",
      productId: generic[0]?.productId || "",
      reason: "single generic token mapping",
      mapping: generic[0],
    };
  }

  const unconfirmed = mappings.find((mapping) =>
    mapping.status === "unconfirmed" &&
    mapping.branchContains.some((token) => normalizeText(ctx.branch).includes(normalizeText(token)))
  );
  if (unconfirmed) {
    return {
      mode: "assigned",
      reason: `unconfirmed candidate ${unconfirmed.candidate || ""}`.trim(),
      mapping: unconfirmed,
    };
  }

  return { mode: "assigned", reason: "no current-project mapping matched" };
}

function readProjectCache() {
  if (!fs.existsSync(PROJECT_CACHE_PATH)) return {};
  try {
    return JSON.parse(fs.readFileSync(PROJECT_CACHE_PATH, "utf8"));
  } catch {
    return {};
  }
}

function cachedProjectId(projectName) {
  const cache = readProjectCache();
  const item = cache[projectName];
  if (!item) return "";
  if (typeof item === "string") return item;
  return `${item.projectId || ""}`;
}

function writeProjectCache(projectName, projectId, source) {
  if (!projectName || !projectId) return;
  const cache = readProjectCache();
  cache[projectName] = {
    projectId: `${projectId}`,
    source: source || "live-discovery",
    updatedAt: new Date().toISOString(),
  };
  fs.mkdirSync(path.dirname(PROJECT_CACHE_PATH), { recursive: true });
  fs.writeFileSync(PROJECT_CACHE_PATH, JSON.stringify(cache, null, 2), "utf8");
}

function loadCredential() {
  if (process.env.ZENTAO_USER && process.env.ZENTAO_PASS) {
    return { username: process.env.ZENTAO_USER, password: process.env.ZENTAO_PASS };
  }
  const credentialPath = path.join(os.homedir(), ".codex", "secrets", "zentao-bug-triage", "zentao.credential.xml");
  if (!fs.existsSync(credentialPath)) {
    throw new Error(`Missing saved Zentao credential: ${credentialPath}`);
  }
  const ps = [
    "$ErrorActionPreference='Stop'",
    `$cred = Import-Clixml -LiteralPath ${JSON.stringify(credentialPath)}`,
    "$obj = @{ username = $cred.UserName; password = $cred.GetNetworkCredential().Password }",
    "$obj | ConvertTo-Json -Compress",
  ].join("; ");
  const out = cp.execFileSync("powershell.exe", ["-NoProfile", "-Command", ps], { encoding: "utf8" });
  const parsed = JSON.parse(out);
  if (!parsed.username || !parsed.password) throw new Error("Saved Zentao credential is empty");
  return parsed;
}

async function loginIfNeeded(page, credentials) {
  await page.goto(`${SITE_URL}/my.html`, { waitUntil: "domcontentloaded", timeout: 60000 });
  const loginInput = page.locator('input[name="account"], input[name="username"], input#account').first();
  if (await loginInput.count()) {
    await loginInput.fill(credentials.username);
    const passwordInput = page.locator('input[name="password"], input#password, input[type="password"]').first();
    await passwordInput.fill(credentials.password);
    const submit = page.locator('button[type="submit"], #submit, input[type="submit"]').first();
    await Promise.all([
      page.waitForLoadState("networkidle", { timeout: 60000 }).catch(() => {}),
      submit.click(),
    ]);
  }
  if (page.url().includes("login")) {
    throw new Error("Zentao login failed. Confirm the saved username/password.");
  }
}

async function findContentFrame(page, pattern) {
  let best = page.mainFrame();
  let bestScore = -1;
  for (const frame of page.frames()) {
    const score = await frame.evaluate((source) => {
      const text = document.body?.innerText || "";
      const links = Array.from(document.querySelectorAll("a")).filter((a) => /bug-view-\d+/.test(a.href)).length;
      const re = new RegExp(source);
      return (re.test(text) ? 1000 : 0) + links * 10 + text.length / 10000;
    }, pattern.source).catch(() => -1);
    if (score > bestScore) {
      best = frame;
      bestScore = score;
    }
  }
  return best;
}

async function waitForContentFrame(page, pattern, timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs;
  let best = page.mainFrame();
  while (Date.now() < deadline) {
    best = await findContentFrame(page, pattern);
    const matched = await best.evaluate((source) => {
      const text = document.body?.innerText || "";
      const links = Array.from(document.querySelectorAll("a")).filter((a) => /bug-view-\d+/.test(a.href)).length;
      return new RegExp(source).test(text) || links > 0;
    }, pattern.source).catch(() => false);
    if (matched) return best;
    await page.waitForTimeout(500);
  }
  return best;
}

async function extractBugRows(page) {
  const frame = await waitForContentFrame(page, /Bug标题|指派给我|bug-view-\d+/);
  return await frame.evaluate(() => {
    const htmlToText = (html) => {
      const div = document.createElement("div");
      div.innerHTML = html || "";
      return div.innerText.replace(/\n{3,}/g, "\n\n").trim();
    };
    const dtable = document.querySelector("[zui-create-dtable]");
    if (dtable) {
      try {
        const config = Function(`return (${dtable.getAttribute("zui-create-dtable")})`)();
        const typeCol = (config.cols || []).find((col) => col.name === "type");
        const typeMap = typeCol?.map || {};
        return Object.values(config.data || {}).map((item) => {
          const id = `${item.id || ""}`;
          return {
            id,
            href: new URL(`/zentao/bug-view-${id}.html`, location.origin).href,
            title: item.title || "",
            product: item.productName || "",
            severity: item.severity || item.severityOrder || "",
            priority: item.pri || item.priOrder || "",
            bugType: typeMap[item.type] || item.type || "",
            status: item.status || "",
            assignedTo: item.assignedTo || "",
            openedBy: item.openedBy || "",
            openedDate: item.openedDate || "",
            steps: htmlToText(item.steps || ""),
            rawCells: [],
          };
        }).filter((row) => row.id && row.title);
      } catch {
        // Fall through to DOM link parsing.
      }
    }

    const rows = Array.from(document.querySelectorAll("table tbody tr"));
    const tableRows = rows.map((tr) => {
      const cells = Array.from(tr.querySelectorAll("td")).map((td) => td.innerText.replace(/\s+/g, " ").trim());
      const link = Array.from(tr.querySelectorAll("a")).find((a) => /bug-view-\d+/.test(a.href));
      const href = link ? link.href : "";
      const idMatch = (href + " " + cells.join(" ")).match(/bug-view-(\d+)|\b(\d{3,6})\b/);
      const id = idMatch ? (idMatch[1] || idMatch[2]) : "";
      if (!id || !href) return null;
      return {
        id,
        href,
        title: link.innerText.replace(/\s+/g, " ").trim(),
        severity: cells[2] || "",
        priority: cells[3] || "",
        status: cells[4] || "",
        openedBy: cells[5] || "",
        openedDate: cells[6] || "",
        assignedTo: cells[8] || "",
        rawCells: cells,
      };
    }).filter(Boolean);
    if (tableRows.length) return tableRows;

    return Array.from(document.querySelectorAll("a"))
      .filter((a) => /bug-view-\d+/.test(a.href))
      .map((a) => {
        const id = (a.href.match(/bug-view-(\d+)/) || [])[1] || "";
        return {
          id,
          href: a.href,
          title: a.innerText.replace(/\s+/g, " ").trim(),
          rawCells: [],
        };
      })
      .filter((row, index, arr) => row.id && arr.findIndex((x) => x.id === row.id) === index);
  });
}

async function gotoNextPage(page) {
  const frame = await waitForContentFrame(page, /共\s*\d+\s*页|Bug标题|bug-view-\d+/);
  const candidates = [
    ".pager a[title='下一页']",
    ".pager a.next",
    "a:has-text('下一页')",
    "a:has-text('›')",
    "a:has-text('>')",
  ];
  for (const sel of candidates) {
    const loc = frame.locator(sel).last();
    if (await loc.count()) {
      const cls = await loc.evaluate((el) => `${el.className} ${el.parentElement?.className || ""}`).catch(() => "");
      if (/disabled/.test(cls)) return false;
      await Promise.all([
        page.waitForLoadState("domcontentloaded", { timeout: 60000 }).catch(() => {}),
        loc.click(),
      ]);
      await page.waitForTimeout(800);
      return true;
    }
  }
  return false;
}

async function discoverProjectId(page, projectName) {
  if (!projectName) return "";
  const normalizedTarget = normalizeText(projectName);
  const candidateUrls = [
    `${SITE_URL}/project-browse.html`,
    `${SITE_URL}/program-browse.html`,
  ];

  for (const url of candidateUrls) {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForTimeout(1000);
    for (const frame of page.frames()) {
      const matches = await frame.evaluate((target) => {
        const norm = (value) => (value || "").toLowerCase().replace(/\s+/g, "").trim();
        return Array.from(document.querySelectorAll("a"))
          .map((a) => ({
            text: (a.innerText || a.textContent || "").replace(/\s+/g, " ").trim(),
            href: a.href || "",
          }))
          .filter((a) => /project-index-\d+/.test(a.href))
          .filter((a) => {
            const text = norm(a.text);
            return text === target || text.includes(target) || target.includes(text);
          });
      }, normalizedTarget).catch(() => []);
      if (matches.length) {
        const exact = matches.find((item) => normalizeText(item.text) === normalizedTarget) || matches[0];
        const id = (exact.href.match(/project-index-(\d+)/) || [])[1] || "";
        if (id) return id;
      }
    }
  }
  return "";
}

async function resolveProjectBugUrl(page, projectId, bugStatus) {
  const baseUrl = `${SITE_URL}/project-bug-${projectId}.html`;
  const status = normalizeText(bugStatus || "all");
  if (!projectId || status === "all") return baseUrl;

  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(1000);

  const textByStatus = {
    unresolved: "未解决",
    active: "未解决",
    closed: "已关闭",
  };
  const targetText = textByStatus[status];
  if (!targetText) return baseUrl;

  for (const frame of page.frames()) {
    const href = await frame.evaluate((target) => {
      const links = Array.from(document.querySelectorAll("a")).map((a) => ({
        text: (a.innerText || a.textContent || "").replace(/\s+/g, " ").trim(),
        href: a.href || "",
      }));
      const exact = links.find((a) => a.text.includes(target) && /project-bug-\d+/.test(a.href));
      return exact ? exact.href : "";
    }, targetText).catch(() => "");
    if (href) return href;
  }

  return baseUrl;
}

function productBugUrl(productId, bugStatus) {
  if (!productId) return "";
  const status = normalizeText(bugStatus || "all");
  if (status === "closed") return `${SITE_URL}/bug-browse-${productId}-closed-.html`;
  if (status === "resolved") return `${SITE_URL}/bug-browse-${productId}-resolved-.html`;
  return `${SITE_URL}/bug-browse-${productId}-all-.html`;
}

function classify(bug) {
  const issueText = `${bug.title}\n${bug.steps || ""}`.toLowerCase();
  const text = `${issueText}\n${bug.product || ""}`.toLowerCase();
  const has = (words) => words.some((w) => text.includes(w.toLowerCase()));
  const hasIssue = (words) => words.some((w) => issueText.includes(w.toLowerCase()));
  let category = "不明确";
  let difficulty = "中";
  let logsNeeded = false;
  let canHandle = "需确认信息";
  let advice = "补充复现步骤、截图或日志后再判断。";

  const contactCountIssue = has(["白名单", "联系人", "通讯录"]) &&
    has(["最多", "数量", "上限", "16", "25", "展示"]);
  const bindingTextIssue = has(["绑定向导", "绑定app", "请绑定app", "提示语"]) &&
    has(["改成", "换成", "提示", "小程序", "设备"]);
  const certificationTextIssue = has(["3c", "认证信息", "扰码"]) &&
    has(["冒号", "6位", "前6位", "不正确"]);
  const factoryOrAgingIssue = has(["工模", "老化模式", "自动老化", "lcd", "喇叭", "麦克", "振动", "马达"]);
  const pedometerTextIssue = has(["计步"]) &&
    has(["显示错误", "文字", "记录"]);
  const pedometerDataIssue = has(["计步", "步伐"]) &&
    has(["无数据", "显示错误", "记录", "步伐测试"]);
  const lockOrOrderUiIssue = has(["锁机", "一级ui", "顺序", "学生证", "绑定信息"]);
  const classModePriorityIssue = has(["课堂模式", "免打扰"]) &&
    has(["冲突", "优先级", "下发", "时段"]);

  if (contactCountIssue) {
    category = "业务/协议/应用层";
    difficulty = "中";
    logsNeeded = false;
    canHandle = "可以先查";
    advice = "先查联系人/白名单协议解析、NVM槽位和电话本UI数量边界。";
  } else if (bindingTextIssue || certificationTextIssue || lockOrOrderUiIssue || pedometerTextIssue) {
    category = "UI Bug";
    difficulty = "低";
    logsNeeded = false;
    canHandle = "可以先查";
    advice = "描述或截图已指向文案/布局问题，先进入当前分支代码排查队列。";
  } else if (factoryOrAgingIssue || pedometerDataIssue) {
    category = "业务/协议/应用层";
    difficulty = "中";
    logsNeeded = hasIssue(["偶现", "无数据", "log", "日志"]);
    canHandle = logsNeeded ? "需要日志后再查" : "可以先查";
    advice = logsNeeded ? "已有工模/日志线索时先查当前分支传感器/工模状态链路。" : "先查工模、设置项或对应功能入口实现。";
  } else if (classModePriorityIssue) {
    category = "业务/协议/应用层";
    difficulty = "中";
    logsNeeded = true;
    canHandle = "需要日志后再查";
    advice = "先确认后台/小程序下发包和本地课堂模式优先级处理，再判断是否平台侧或固件侧。";
  } else if (has(["底电流", "pmic", "ldo", "sim removed", "sdio", "modem", "sensor", "mclk", "死机", "crash", "assert", "dump", "驱动", "充电电流"])) {
    category = "底层/硬件/驱动";
    difficulty = "高";
    logsNeeded = true;
    canHandle = "不直接处理-底层";
    advice = "需要CATStudio/功耗/硬件版本/原理图证据，先给底层或硬件定位建议。";
  } else if (has(["后台", "平台", "服务器", "接口", "云端", "管理端", "账号", "权限", "数据库"])) {
    category = "平台端";
    difficulty = "高";
    logsNeeded = true;
    canHandle = "不直接处理-平台";
    advice = "需要平台接口请求/响应或后台配置证据，先确认是否设备请求错误。";
  } else if (has(["界面", "显示不全", "显示错误", "图标", "导航栏", "按钮", "页面", "弹窗", "文案", "字体", "布局", "滚动", "am pm", "12小时", "灰色", "闹钟"])) {
    category = "UI Bug";
    difficulty = "低";
    logsNeeded = false;
    canHandle = "可以先查";
    advice = "先在当前分支确认页面和状态刷新路径，再做局部UI修复。";
  } else if (has(["app", "小程序", "协议", "指令", "上报", "下发", "短信", "微聊", "联系人", "白名单", "sos", "bullyevent", "定位", "云相册", "消息", "imei", "重启"])) {
    category = "业务/协议/应用层";
    difficulty = "中";
    logsNeeded = hasIssue(["上报", "下发", "协议", "指令", "app", "小程序"]);
    canHandle = logsNeeded ? "需要日志后再查" : "可以先查";
    advice = logsNeeded ? "需要协议包/APP操作日志确认字段和时序，再查代码。" : "先查业务状态机、协议解析和本地存储路径。";
  }

  return { category, difficulty, logsNeeded, canHandle, advice };
}

function hasRelevantEvidence(bug) {
  const links = [...(bug.attachmentLinks || []), ...(bug.attachments || [])];
  return links.some((link) =>
    /\.(log|txt|zip|rar|7z|mp4|avi|mov|png|jpe?g)(?:$|[?#]|\s|\))/i.test(`${link.href || ""} ${link.url || ""} ${link.name || ""} ${link.text || ""}`)
  );
}

function hasClearExpectation(bug) {
  const expected = `${bug.expected || ""}\n${bug.stepSections?.expected || ""}\n${bug.lastActivation?.expected || ""}`.trim();
  if (expected && !/^\[?期望\]?$/.test(expected)) return true;
  const text = `${bug.title || ""}\n${bug.steps || ""}`;
  return /需要|应该|改成|换成|去掉|加上|不能出现|按照|优先级|显示为|提示/.test(text);
}

function decideHandling(bug) {
  const statusText = normalizeText(bug.status);
  if (/已解决|已关闭|关闭|resolved|closed/.test(statusText)) {
    return {
      handlingAction: "ignore",
      handlingBucket: "ignored",
      handlingLabel: "本轮不处理",
      handlingReason: "禅道状态显示已解决/已关闭，除非用户明确要求回归确认。",
    };
  }
  if (/不直接处理-底层/.test(bug.canHandle || "") || bug.category === "底层/硬件/驱动") {
    return {
      handlingAction: "ignore",
      handlingBucket: "ignored",
      handlingLabel: "本轮不处理",
      handlingReason: "偏底层/硬件/驱动问题，需要硬件、驱动或平台日志链路，Codex不直接改业务代码。",
    };
  }
  if (/不直接处理-平台/.test(bug.canHandle || "") || bug.category === "平台端") {
    return {
      handlingAction: "ignore",
      handlingBucket: "ignored",
      handlingLabel: "本轮不处理",
      handlingReason: "偏平台/后台/账号配置问题，需要平台请求响应或后台配置证据。",
    };
  }
  if (/需确认项目|需确认信息/.test(bug.canHandle || "") || bug.category === "不明确") {
    if (hasRelevantEvidence(bug) || hasClearExpectation(bug)) {
      return {
        handlingAction: "review",
        handlingBucket: "work",
        handlingLabel: "待判断/可查",
        handlingReason: "虽然自动分类不够明确，但已有明确期望或附件证据，先进入候选检查队列，避免漏掉可修问题。",
      };
    }
    return {
      handlingAction: "confirm",
      handlingBucket: "ignored",
      handlingLabel: "等确认",
      handlingReason: "描述或归属不够明确，先等复现步骤、期望行为、项目/分支或截图日志确认。",
    };
  }
  if (/需要日志后再查/.test(bug.canHandle || "") && !hasRelevantEvidence(bug)) {
    if (hasClearExpectation(bug) && !/平台端|底层\/硬件\/驱动/.test(bug.category || "")) {
      return {
        handlingAction: "review",
        handlingBucket: "work",
        handlingLabel: "待判断/可查",
        handlingReason: "问题有明确期望但缺少日志，先列为候选检查；代码侧能否修复需排查后再定。",
      };
    }
    return {
      handlingAction: "need-log",
      handlingBucket: "ignored",
      handlingLabel: "等日志",
      handlingReason: "协议、上报、时序或网络类问题缺关键日志/附件，当前不适合直接改代码。",
    };
  }
  return {
    handlingAction: "inspect",
    handlingBucket: "work",
    handlingLabel: "需要检查/可修",
    handlingReason: "当前分类属于UI、应用或协议层，且已有足够描述或附件，可以进入代码排查和修复队列。",
  };
}

function finalizeBug(bug) {
  const decision = decideHandling(bug);
  if (bug.reactivated && decision.handlingBucket === "work") {
    return {
      ...bug,
      ...decision,
      handlingAction: "reactivated",
      handlingLabel: "复测激活-需要检查",
      handlingReason: "该 bug 曾被解决后又被测试激活，当前问题以后续激活说明为准。",
    };
  }
  if (bug.reactivated && decision.handlingAction === "need-log") {
    return {
      ...bug,
      ...decision,
      handlingLabel: "复测激活-等日志",
      handlingReason: "该 bug 曾被解决后又被测试激活，但仍缺协议包、日志或附件证据，先不要直接改代码。",
    };
  }
  return { ...bug, ...decision };
}

function rowMatchesFilter(row, args) {
  const product = normalizeText(row.product || "");
  const title = normalizeText(row.title || "");
  if (args.projectName) {
    const project = normalizeText(args.projectName);
    if (product) return projectNameMatches(row.product, args.projectName);
    if (!title.includes(project)) return false;
  }
  if (args.projectKey) {
    const keys = splitListValue(args.projectKey).map(normalizeText);
    const haystack = normalizeText(`${row.product || ""} ${row.title || ""}`);
    if (keys.length && !keys.every((key) => haystack.includes(key))) return false;
  }
  return true;
}

function isMineAssignedFilter(args) {
  const assignedTo = normalizeText(args.assignedTo || "");
  return ["me", "mine", "self", "current", "我", "自己", "当前账号"].includes(assignedTo);
}

function rowMatchesAssignedTo(row, args) {
  if (!args.assignedTo || isMineAssignedFilter(args)) return true;
  const assignedTo = normalizeText(row.assignedTo || "");
  if (!assignedTo) return false;
  const targets = splitListValue(args.assignedTo).map(normalizeText).filter(Boolean);
  if (!targets.length) return true;
  return targets.some((target) => assignedTo === target || assignedTo.includes(target) || target.includes(assignedTo));
}

function projectNameMatches(value, projectName) {
  const product = normalizeText(value || "");
  const project = normalizeText(projectName || "");
  if (!product || !project) return false;
  return product === project || product.includes(project) || project.includes(product);
}

function rowMatchesBugStatus(row, args) {
  const requested = normalizeText(args.bugStatus || "all");
  if (!requested || requested === "all") return true;
  const status = normalizeText(row.status || "");
  if (requested === "unresolved" || requested === "active") {
    return /^(active|激活|opened|open|未解决)$/.test(status);
  }
  if (requested === "closed" || requested === "resolved") {
    return /^(closed|resolved|已关闭|已解决|关闭|解决)$/.test(status);
  }
  return true;
}

const FIELD_LABELS = [
  "所属产品", "所属项目", "Bug类型", "严重程度", "优先级", "Bug状态", "指派给", "由谁创建",
  "创建日期", "创建时间", "指派日期", "指派时间", "最后修改", "最后编辑", "解决日期",
  "解决时间", "关闭日期", "关闭时间", "重现步骤", "步骤", "结果", "实际结果", "期望",
  "预期", "期望结果", "附件", "历史记录", "基本信息", "Bug的一生",
];

function cleanFieldValue(value) {
  const text = (value || "").replace(/\s+/g, " ").trim();
  if (!text) return "";
  const normalized = text.replace(/[\[\]【】:：。.\s]/g, "");
  if (FIELD_LABELS.some((label) => normalized === label)) return "";
  return text;
}

function parseField(text, label) {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const lines = (text || "").replace(/\r/g, "").split(/\n/);
  for (let index = 0; index < lines.length; index++) {
    const line = lines[index].trim();
    if (!line) continue;
    if (line === label || line === `[${label}]`) {
      for (let next = index + 1; next < lines.length; next++) {
        const value = cleanFieldValue(lines[next]);
        if (value) return value;
        if (FIELD_LABELS.includes(lines[next].trim().replace(/[\[\]]/g, ""))) break;
      }
    }
    const sameLine = line.match(new RegExp(`^${escaped}\\s*[:：]?\\s+(.+)$`));
    if (sameLine) {
      const value = cleanFieldValue(sameLine[1]);
      if (value) return value;
    }
  }
  const re = new RegExp(`${escaped}\\s+([^\\n]+)`);
  const m = (text || "").match(re);
  return m ? cleanFieldValue(m[1]) : "";
}

function parseFieldAny(text, labels) {
  for (const label of labels) {
    const value = parseField(text, label);
    if (value) return value;
  }
  return "";
}

function parseDateNear(text, labels) {
  for (const label of labels) {
    const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const re = new RegExp(`${escaped}[\\s\\S]{0,100}?((?:19|20)\\d{2}[-/]\\d{1,2}[-/]\\d{1,2}(?:\\s+\\d{1,2}:\\d{2}(?::\\d{2})?)?)`);
    const m = text.match(re);
    if (m) return m[1].trim();
  }
  return "";
}

function extractStepSections(text) {
  let source = (text || "").replace(/\r/g, "").trim();
  const sections = { steps: "", actual: "", expected: "" };
  if (!source) return sections;

  const labelPattern = "步骤|操作步骤|重现步骤|结果|实际结果|期望|预期|期望结果";
  source = source
    .replace(new RegExp(`\\s*\\[(${labelPattern})\\]\\s*`, "g"), "\n[$1]\n")
    .replace(new RegExp(`\\s*【(${labelPattern})】\\s*`, "g"), "\n[$1]\n")
    .replace(new RegExp(`\\s+(${labelPattern})\\s*[:：]\\s*`, "g"), "\n$1:\n")
    .trim();
  const re = new RegExp(`(?:^|\\n)\\s*(?:\\[(${labelPattern})\\]|(${labelPattern})\\s*[:：])[ \\t]*\\n?([\\s\\S]*?)(?=(?:\\n\\s*(?:\\[(?:${labelPattern})\\]|(?:${labelPattern})\\s*[:：]))|$)`, "g");
  let found = false;
  let match;
  while ((match = re.exec(source)) !== null) {
    found = true;
    const label = match[1] || match[2] || "";
    const body = (match[3] || "").replace(/\n+附件\s*[\s\S]*$/m, "").trim();
    if (!body) continue;
    if (/期望|预期/.test(label)) sections.expected = body;
    else if (/结果/.test(label)) sections.actual = body;
    else if (/步骤/.test(label)) sections.steps = body;
  }
  if (!found) sections.steps = source;
  return sections;
}

function normalizeAttachmentLinks(links) {
  const seen = new Set();
  const result = [];
  for (const link of links || []) {
    if (!link.href || /-left\.html(?:$|[?#])/i.test(link.href)) continue;
    const key = link.href.replace(/[?&]zentaosid=[^&]+/i, "");
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(link);
  }
  return result;
}

function cleanHistoryNote(note) {
  return (note || "")
    .replace(/\r/g, "")
    .replace(/\n+(返回|指派|解决|转研发需求|转任务|编辑|复制|删除)\s*(\n[\s\S]*)?$/m, "")
    .replace(/\n+(基本信息|所属模块|所属计划|来源用例|项目\/迭代\/研发需求\/任务|其他相关|操作系统|浏览器|关键词|抄送给)\s*[\s\S]*$/m, "")
    .trim();
}

function parseHistoryRecords(text) {
  const source = (text || "").replace(/\r/g, "");
  const start = source.lastIndexOf("历史记录");
  if (start < 0) return [];
  const tail = source.slice(start);
  const recordRe = /(?:^|\n)\s*(\d+)\s*\n?\s*((?:19|20)\d{2}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}:\d{2})\s*[，,]\s*由\s+([^\s，,。]+)\s+([^\n]+)/g;
  const starts = [];
  let match;
  while ((match = recordRe.exec(tail)) !== null) {
    starts.push({
      index: match.index,
      end: match.index + match[0].length,
      order: match[1],
      date: match[2],
      actor: match[3],
      summary: match[4].replace(/\s+/g, " ").trim(),
    });
  }

  return starts.map((item, index) => {
    const nextIndex = index + 1 < starts.length ? starts[index + 1].index : tail.length;
    const note = cleanHistoryNote(tail.slice(item.end, nextIndex));
    const stepSections = extractStepSections(note);
    let action = "other";
    if (/激活|重新打开|reopen/i.test(item.summary)) action = "activated";
    else if (/解决|resolved/i.test(item.summary)) action = "resolved";
    else if (/关闭|closed/i.test(item.summary)) action = "closed";
    else if (/指派|assigned/i.test(item.summary)) action = "assigned";
    else if (/创建|opened|create/i.test(item.summary)) action = "created";
    return {
      order: item.order,
      date: item.date,
      actor: item.actor,
      summary: item.summary,
      action,
      note,
      stepSections,
      actual: stepSections.actual,
      expected: stepSections.expected,
    };
  });
}

function lastActivationRecord(records) {
  const activations = (records || []).filter((record) => record.action === "activated");
  return activations.length ? activations[activations.length - 1] : null;
}

function shouldDownloadAttachments(args, bug) {
  if (args.downloadMode === "all") return true;
  if (args.downloadMode === "none") return false;
  if (args.ids.length > 0) return true;
  if (bug.logsNeeded) return true;
  return (bug.attachmentLinks || []).some((link) => Boolean(knownExtensionFromText(`${link.href || ""} ${link.text || ""}`)));
}

function knownExtensionFromText(value) {
  const match = `${value || ""}`.match(/\.(log|txt|zip|rar|7z|mp4|avi|mov|png|jpe?g)(?:$|[?#]|\s|\))/i);
  return match ? `.${match[1].toLowerCase().replace("jpeg", "jpg")}` : "";
}

function extensionFromContentType(contentType) {
  const type = `${contentType || ""}`.toLowerCase();
  if (type.includes("png")) return ".png";
  if (type.includes("jpeg") || type.includes("jpg")) return ".jpg";
  if (type.includes("zip")) return ".zip";
  if (type.includes("rar")) return ".rar";
  if (type.includes("7z")) return ".7z";
  if (type.includes("mp4")) return ".mp4";
  if (type.includes("quicktime")) return ".mov";
  if (type.includes("plain")) return ".txt";
  return "";
}

function attachmentFileName(link, index, response) {
  const raw = (link.text || `attachment-${index + 1}`)
    .replace(/\s*\([^)]*(?:KB|MB|GB|字节|Bytes)[^)]*\)\s*$/i, "")
    .trim();
  let name = raw || `attachment-${index + 1}`;
  name = name.replace(/[<>:"/\\|?*\x00-\x1F]/g, "_").slice(0, 120).trim();
  if (!name) name = `attachment-${index + 1}`;

  const known = knownExtensionFromText(name);
  if (known && name.toLowerCase().endsWith(known)) return name;

  const hrefExt = knownExtensionFromText(link.href);
  const typeExt = extensionFromContentType(response?.headers?.()["content-type"]);
  const ext = known || hrefExt || typeExt;
  if (ext && !name.toLowerCase().endsWith(ext)) name += ext;
  return name;
}

function compactError(error) {
  return `${error?.message || error || "unknown error"}`.replace(/\s+/g, " ").trim().slice(0, 300);
}

function detailAttemptCount(args) {
  const retries = Number.isFinite(args.detailRetries) ? Math.max(0, args.detailRetries) : 2;
  return retries + 1;
}

function detailTimeoutMs(args) {
  return Number.isFinite(args.detailTimeoutMs) && args.detailTimeoutMs > 0 ? args.detailTimeoutMs : 60000;
}

async function gotoBugDetailWithRetry(page, row, args) {
  const attempts = detailAttemptCount(args);
  let lastError;
  for (let attempt = 1; attempt <= attempts; attempt++) {
    const startedAt = Date.now();
    try {
      await page.goto(row.href, { waitUntil: "domcontentloaded", timeout: detailTimeoutMs(args) });
      return { attempt, elapsedMs: Date.now() - startedAt };
    } catch (error) {
      lastError = error;
      await page.evaluate(() => window.stop()).catch(() => {});
      if (attempt >= attempts) break;
      console.warn(`[zentao-bug-triage] Detail page retry ${attempt}/${attempts} for bug #${row.id}: ${compactError(error)}`);
      await page.waitForTimeout(Math.min(5000, 1200 * attempt));
    }
  }
  throw lastError;
}

async function extractBugDetail(page, row, attachmentDir, args) {
  const detailNav = await gotoBugDetailWithRetry(page, row, args);
  await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(1000);
  const frame = await waitForContentFrame(page, new RegExp(`重现步骤|Bug类型|严重程度|Bug的一生|${row.id}`), 20000);
  const detail = await frame.evaluate(() => {
    const bodyText = document.body.innerText.replace(/\r/g, "");
    const title = (document.querySelector("h1")?.innerText || document.title || "").replace(/\s+/g, " ").trim();
    const links = Array.from(document.querySelectorAll("a")).map((a) => ({
      text: a.innerText.replace(/\s+/g, " ").trim(),
      href: a.href,
    })).filter((a) => /file|download|attachment|\.log|\.txt|\.zip|\.rar|\.7z|\.png|\.jpg|\.jpeg/i.test(`${a.text} ${a.href}`));
    return { bodyText, title, links };
  });
  const stepsMatch = detail.bodyText.match(/重现步骤\s*([\s\S]*?)(历史记录|基本信息|Bug的一生|$)/);
  const titleMatch = detail.title.match(/^BUG #\d+\s+(.+?)\s+-\s+(.+?)\s+-\s+禅道$/);
  const steps = row.steps || (stepsMatch ? stepsMatch[1].trim() : "");
  const product = row.product || parseField(detail.bodyText, "所属产品") || (titleMatch ? titleMatch[2] : "") || row.rawCells[5] || "";
  const bugType = row.bugType || parseField(detail.bodyText, "Bug类型") || row.rawCells[4] || "";
  const severity = row.severity || parseField(detail.bodyText, "严重程度") || row.rawCells[2] || "";
  const priority = row.priority || parseField(detail.bodyText, "优先级") || row.rawCells[3] || "";
  const status = row.status || parseField(detail.bodyText, "Bug状态") || "";
  const assignedTo = row.assignedTo || parseField(detail.bodyText, "指派给") || "";
  const openedDate = row.openedDate || parseDateNear(detail.bodyText, ["创建日期", "创建时间", "由谁创建", "Opened"]);
  const assignedDate = parseDateNear(detail.bodyText, ["指派日期", "指派时间", "Assigned"]);
  const editedDate = parseDateNear(detail.bodyText, ["最后修改", "最后编辑", "Edited"]);
  const resolvedDate = parseDateNear(detail.bodyText, ["解决日期", "解决时间", "Resolved"]);
  const closedDate = parseDateNear(detail.bodyText, ["关闭日期", "关闭时间", "Closed"]);
  const stepSections = extractStepSections(steps);
  const expected = parseFieldAny(detail.bodyText, ["期望", "预期", "期望结果"]) || stepSections.expected;
  const actual = parseFieldAny(detail.bodyText, ["结果", "实际结果"]) || stepSections.actual;
  const attachmentLinks = normalizeAttachmentLinks(detail.links);
  const historyRecords = parseHistoryRecords(detail.bodyText);
  const lastActivation = lastActivationRecord(historyRecords);
  const activationCount = Number(parseField(detail.bodyText, "激活次数")) || historyRecords.filter((record) => record.action === "activated").length;

  let bug = {
    id: row.id,
    url: row.href,
    title: row.title || (titleMatch ? titleMatch[1] : detail.title),
    product,
    bugType,
    severity,
    priority,
    status,
    openedBy: row.openedBy || parseField(detail.bodyText, "由谁创建") || "",
    assignedTo,
    openedDate,
    assignedDate,
    editedDate,
    resolvedDate,
    closedDate,
    steps,
    stepSections,
    actual,
    expected,
    historyRecords,
    activationCount,
    lastActivation,
    reactivated: Boolean(lastActivation),
    attachmentLinks,
    attachments: [],
    detailFetchAttempts: detailNav.attempt,
    detailFetchMs: detailNav.elapsedMs,
  };
  bug = { ...bug, ...classify(bug) };

  const attachments = [];
  if (shouldDownloadAttachments(args, bug) && attachmentLinks.length) {
    fs.mkdirSync(attachmentDir, { recursive: true });
    for (const [idx, link] of attachmentLinks.entries()) {
      const res = await page.request.get(link.href).catch(() => null);
      if (res && res.ok()) {
        const cleanName = attachmentFileName(link, idx, res);
        const target = path.join(attachmentDir, cleanName);
        fs.writeFileSync(target, await res.body());
        attachments.push({ name: cleanName, url: link.href, path: target });
      } else {
        const cleanName = attachmentFileName(link, idx, res);
        attachments.push({ name: cleanName, url: link.href, path: "" });
      }
    }
  }
  bug.attachments = attachments;
  bug.detailFetched = true;
  return finalizeBug(bug);
}

function bugFromDetailError(row, args, error) {
  const bug = bugFromRow(row, args);
  bug.detailFetchError = compactError(error);
  bug.detailFetchAttempts = detailAttemptCount(args);
  bug.advice = `${bug.advice || ""}${bug.advice ? "；" : ""}详情页抓取失败，本轮保留列表摘要，修复前需用 --ids 重试深抓或手动确认详情`;
  bug.handlingReason = `${bug.handlingReason || ""}${bug.handlingReason ? "；" : ""}详情页抓取失败：${bug.detailFetchError}`;
  return bug;
}

function bugFromRow(row, args) {
  const cells = row.rawCells || [];
  const stepSections = extractStepSections(row.steps || "");
  const bug = {
    id: row.id,
    url: row.href,
    title: row.title || "",
    product: row.product || args.projectName || "",
    bugType: row.bugType || "",
    severity: row.severity || cells[2] || "",
    priority: row.priority || cells[3] || "",
    status: row.status || "",
    openedBy: row.openedBy || "",
    assignedTo: row.assignedTo || "",
    openedDate: row.openedDate || "",
    assignedDate: "",
    editedDate: "",
    resolvedDate: "",
    closedDate: "",
    steps: row.steps || "",
    stepSections,
    actual: stepSections.actual,
    expected: stepSections.expected,
    historyRecords: [],
    activationCount: 0,
    lastActivation: null,
    reactivated: false,
    attachmentLinks: [],
    attachments: [],
    detailFetched: false,
  };
  return finalizeBug({ ...bug, ...classify(bug) });
}

function slug(s) {
  return (s || "unknown").replace(/[<>:"/\\|?*\x00-\x1F]/g, "_").replace(/\s+/g, "_").slice(0, 80);
}

function markdownReport(ctx, bugs) {
  const lines = [];
  lines.push(`# Zentao Bug Snapshot`);
  lines.push("");
  lines.push(`- 时间：${new Date().toLocaleString("zh-CN", { hour12: false })}`);
  if (ctx.repoName) lines.push(`- Worktree：${ctx.repoName}`);
  lines.push(`- Repo：${ctx.repo}`);
  lines.push(`- 分支：${ctx.branch}`);
  lines.push(`- 提交：${ctx.commit}`);
  lines.push(`- yl_device_ver：${ctx.deviceVer || "未找到"}`);
  if (ctx.deviceName) lines.push(`- yl_device_name：${ctx.deviceName}`);
  if (ctx.projectName) lines.push(`- Zentao项目：${ctx.projectName}`);
  if (ctx.productId) lines.push(`- Zentao产品ID：${ctx.productId}`);
  if (ctx.projectId) lines.push(`- Zentao项目ID：${ctx.projectId}`);
  if (ctx.bugStatus) lines.push(`- Bug状态筛选：${ctx.bugStatus}`);
  if (ctx.assignedToFilter) lines.push(`- 指派筛选：${ctx.assignedToFilter === "me" ? "当前账号" : ctx.assignedToFilter}`);
  if (typeof ctx.assignedScanCount === "number") lines.push(`- 指派给我候选：${ctx.assignedScanCount}`);
  if (ctx.fetchMode) lines.push(`- 抓取模式：${ctx.fetchMode}`);
  if (ctx.projectResolveReason) lines.push(`- 项目匹配：${ctx.projectResolveReason}`);
  lines.push(`- dirty：${ctx.dirty ? "是" : "否"}`);
  lines.push("");
  lines.push("| ID | 标题 | 产品/项目 | 状态 | 严重/优先 | 创建/修改/解决 | 激活 | 详情 | 分类 | 难度 | 本轮处理 | 附件 | 描述摘要 | Codex能否处理 | 建议/原因 |");
  lines.push("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |");
  for (const b of bugs) {
    const attachmentText = `${(b.attachmentLinks || []).length}个链接/${(b.attachments || []).filter((a) => a.path).length}个已下载`;
    const currentNote = b.lastActivation?.note || b.steps || "";
    const stepsSummary = currentNote.replace(/\s+/g, " ").replace(/\|/g, "/").slice(0, 120);
    const dates = [b.openedDate, b.editedDate, b.resolvedDate].map((x) => x || "-").join("/");
    const detailText = b.detailFetched ? "已打开" : (b.detailFetchError ? `失败:${b.detailFetchError}` : "列表");
    const activationText = b.reactivated ? `${b.activationCount || 1}次/${b.lastActivation?.date || ""}` : "-";
    const handling = `${b.handlingLabel || ""}${b.handlingAction ? `(${b.handlingAction})` : ""}`;
    const advice = `${b.advice || ""}${b.handlingReason ? `；${b.handlingReason}` : ""}`.replace(/\|/g, "/");
    lines.push(`| ${b.id} | ${b.title.replace(/\|/g, "/")} | ${(b.product || "").replace(/\|/g, "/")} | ${b.status || ""} | ${b.severity || ""}/${b.priority || ""} | ${dates} | ${activationText} | ${detailText} | ${b.category} | ${b.difficulty} | ${handling} | ${attachmentText} | ${stepsSummary} | ${b.canHandle} | ${advice} |`);
  }
  return lines.join("\n");
}

function compactTitle(value) {
  const text = (value || "").replace(/\s+/g, " ").replace(/\|/g, "/").trim();
  return text.length > 30 ? `${text.slice(0, 29)}...` : text;
}

function compactCategory(bug) {
  if (/UI/.test(bug.category || "")) return "UI";
  if (/平台/.test(bug.category || "")) return "平台";
  if (/底层|硬件|驱动/.test(bug.category || "")) return "底层";
  if (/协议|业务|应用/.test(bug.category || "")) return "应用/协议";
  return bug.category || "不明确";
}

function compactAttachmentText(bug) {
  const values = [...(bug.attachmentLinks || []), ...(bug.attachments || [])]
    .map((item) => `${item.text || ""} ${item.name || ""} ${item.href || ""} ${item.url || ""} ${item.path || ""}`);
  const kinds = [];
  const has = (pattern) => values.some((value) => pattern.test(value));
  if (has(/\.(zip|rar|7z|log|txt)(?:$|[?#]|\s|\))/i) || values.some((value) => /log|日志/i.test(value))) kinds.push("日志");
  if (has(/\.(mp4|mov|avi)(?:$|[?#]|\s|\))/i) || values.some((value) => /视频/i.test(value))) kinds.push("视频");
  if (has(/\.(png|jpe?g)(?:$|[?#]|\s|\))/i) || values.some((value) => /截图|图片/i.test(value))) kinds.push("截图");
  if (!kinds.length && values.length) kinds.push("有");
  return kinds.length ? Array.from(new Set(kinds)).join("+") : "无";
}

function compactHandlingText(bug) {
  if (bug.handlingBucket !== "work") return "先不动";
  if (bug.handlingAction === "review") return "可查";
  if (/需要日志/.test(bug.canHandle || "")) return "可查";
  return "建议修";
}

function compactCanFixText(bug) {
  if (/不直接处理-平台/.test(bug.canHandle || "") || bug.category === "平台端") return "不直接处理";
  if (/不直接处理-底层/.test(bug.canHandle || "") || bug.category === "底层/硬件/驱动") return "不直接处理";
  if (bug.handlingBucket === "work") return "可以先查";
  if (/日志/.test(bug.handlingLabel || "")) return "等日志";
  if (/确认/.test(bug.handlingLabel || "")) return "等确认";
  return bug.canHandle || "待判断";
}

function chatSummaryReport(ctx, bugs, snapshotDir) {
  const lines = [];
  const workCount = bugs.filter((bug) => bug.handlingBucket === "work").length;
  const ignoredCount = bugs.length - workCount;
  const detailFailedCount = bugs.filter((bug) => bug.detailFetchError).length;
  lines.push(`# 当前分支 Bug 简表`);
  lines.push("");
  if (ctx.repoName) lines.push(`- Worktree：${ctx.repoName}`);
  lines.push(`- Repo：${ctx.repo}`);
  lines.push(`- 分支：${ctx.branch}`);
  lines.push(`- 提交：${ctx.commit}`);
  if (ctx.projectName) lines.push(`- 禅道项目：${ctx.projectName}`);
  if (ctx.productId) lines.push(`- 禅道产品ID：${ctx.productId}`);
  if (ctx.fetchMode) lines.push(`- 抓取模式：${ctx.fetchMode}`);
  if (ctx.bugStatus) lines.push(`- Bug状态筛选：${ctx.bugStatus}`);
  if (ctx.assignedToFilter) lines.push(`- 指派筛选：${ctx.assignedToFilter === "me" ? "当前账号" : ctx.assignedToFilter}`);
  if (typeof ctx.assignedScanCount === "number") lines.push(`- 指派给我候选：${ctx.assignedScanCount} 个`);
  lines.push(`- 数量：共 ${bugs.length} 个，候选/可修 ${workCount} 个，先不动 ${ignoredCount} 个`);
  if (detailFailedCount) lines.push(`- 详情失败：${detailFailedCount} 个，已保留列表摘要；修复前需用 --ids 重试深抓`);
  lines.push(`- 快照：${snapshotDir}`);
  lines.push("");
  lines.push("| ID | 标题 | 类型 | 处理建议 | 附件 | 我能否先修 |");
  lines.push("| --- | --- | --- | --- | --- | --- |");
  for (const bug of bugs) {
    lines.push(`| ${bug.id} | ${compactTitle(bug.title)} | ${compactCategory(bug)} | ${compactHandlingText(bug)} | ${compactAttachmentText(bug)} | ${compactCanFixText(bug)} |`);
  }
  return lines.join("\n");
}

function markdownFence(value) {
  const text = (value || "").trim();
  if (!text) return "（空）";
  let fence = "```";
  while (text.includes(fence)) fence += "`";
  return `${fence}text\n${text}\n${fence}`;
}

function oneLine(value) {
  return (value || "").replace(/\s+/g, " ").trim() || "未记录";
}

function currentSectionsForBug(bug) {
  return bug.lastActivation?.stepSections || bug.stepSections || {};
}

function suggestSearchKeywords(bug) {
  const text = `${bug.title || ""}\n${bug.steps || ""}\n${bug.lastActivation?.note || ""}\n${bug.product || ""}`;
  const preferred = [
    "微聊", "白名单", "联系人", "通讯录", "防欺凌", "定位", "GPS", "短信", "消息",
    "录音", "未读", "弹窗", "时间顺序", "查找手表", "响铃", "号码", "昵称",
    "上报", "下发", "协议", "小程序", "BULLYEVENT", "BULLYEVENT1",
  ].filter((word) => text.toLowerCase().includes(word.toLowerCase()));
  const codeLike = text.match(/[A-Za-z_][A-Za-z0-9_]{2,}/g) || [];
  return Array.from(new Set([...preferred, ...codeLike])).slice(0, 24);
}

function workItemsReport(ctx, bugs, snapshotDir) {
  const workItems = bugs.filter((bug) => bug.handlingBucket === "work");
  const lines = [];
  lines.push("# Zentao Bug Work Items");
  lines.push("");
  lines.push("- 用途：临时修复工作单。这里只放本轮建议 Codex 检查/修改的 bug。后续修 bug 时先读这里，不只按标题判断。");
  lines.push("- 注意：如果某条显示“列表”，说明还没打开禅道详情，修复前必须用 `--ids` 深抓该 bug。");
  lines.push(`- 清理：全部修完后运行 \`node "${__filename}" --cleanup "${snapshotDir}"\`，只会删除 work/ignored 临时单和 attachments/。`);
  lines.push(`- 生成时间：${new Date().toLocaleString("zh-CN", { hour12: false })}`);
  lines.push(`- 快照目录：${snapshotDir}`);
  if (ctx.repoName) lines.push(`- Worktree：${ctx.repoName}`);
  lines.push(`- Repo：${ctx.repo}`);
  lines.push(`- 分支：${ctx.branch}`);
  lines.push(`- 提交：${ctx.commit}`);
  if (ctx.projectName) lines.push(`- Zentao项目：${ctx.projectName}`);
  if (ctx.productId) lines.push(`- Zentao产品ID：${ctx.productId}`);
  if (ctx.projectId) lines.push(`- Zentao项目ID：${ctx.projectId}`);
  if (ctx.fetchMode) lines.push(`- 抓取模式：${ctx.fetchMode}`);
  lines.push(`- 工作项数量：${workItems.length}`);
  lines.push(`- 已打开详情：${workItems.filter((bug) => bug.detailFetched).length}`);
  lines.push("");

  for (const bug of workItems) {
    const currentSections = currentSectionsForBug(bug);
    const originalSections = bug.stepSections || {};
    const keywords = suggestSearchKeywords(bug);
    const attachmentLinks = bug.attachmentLinks || [];
    const attachments = bug.attachments || [];
    lines.push(`## Bug #${bug.id} ${oneLine(bug.title)}`);
    lines.push("");
    lines.push(`- 禅道链接：${bug.url}`);
    lines.push(`- 产品/项目：${oneLine(bug.product)}`);
    lines.push(`- 类型：${oneLine(bug.bugType)}`);
    lines.push(`- 状态：${oneLine(bug.status)}`);
    lines.push(`- 详情状态：${bug.detailFetched ? "已打开" : "列表，修复前需深抓详情"}`);
    if (bug.detailFetchError) lines.push(`- 详情失败原因：${oneLine(bug.detailFetchError)}`);
    lines.push(`- 严重/优先：${oneLine(bug.severity)} / ${oneLine(bug.priority)}`);
    lines.push(`- 创建人/指派给：${oneLine(bug.openedBy)} / ${oneLine(bug.assignedTo)}`);
    lines.push(`- 创建/指派/修改/解决/关闭：${oneLine(bug.openedDate)} / ${oneLine(bug.assignedDate)} / ${oneLine(bug.editedDate)} / ${oneLine(bug.resolvedDate)} / ${oneLine(bug.closedDate)}`);
    lines.push(`- 激活次数：${bug.activationCount || 0}`);
    if (bug.reactivated) {
      lines.push(`- 最后激活：${oneLine(bug.lastActivation?.date)} / ${oneLine(bug.lastActivation?.actor)} / ${oneLine(bug.lastActivation?.summary)}`);
    }
    lines.push(`- 分类/难度：${bug.category} / ${bug.difficulty}`);
    lines.push(`- Codex能否处理：${bug.canHandle}`);
    lines.push(`- 本轮处理：${bug.handlingLabel} (${bug.handlingAction})`);
    lines.push(`- 入选原因：${bug.handlingReason}`);
    lines.push(`- 建议：${bug.advice}`);
    lines.push(`- 代码搜索关键词：${keywords.length ? keywords.join("、") : "待人工补充"}`);
    lines.push("");
    lines.push("### 修复记录（临时）");
    lines.push("");
    lines.push("- 排查状态：未开始");
    lines.push("- 相关文件：");
    lines.push("- 根因：");
    lines.push("- 修复思路：");
    lines.push("- 修复提交：");
    lines.push("- 验证结果：");
    lines.push("");
    if (bug.reactivated) {
      lines.push("### 当前复测失败说明（优先）");
      lines.push("");
      lines.push("- 说明：该 bug 已解决后又被激活，后续排查和修复以这里为准。");
      lines.push("");
      lines.push(markdownFence(bug.lastActivation?.note));
      lines.push("");
      lines.push("### 当前复测拆分字段");
      lines.push("");
      lines.push("**步骤**");
      lines.push("");
      lines.push(markdownFence(currentSections.steps));
      lines.push("");
      lines.push("**结果**");
      lines.push("");
      lines.push(markdownFence(bug.lastActivation?.actual || currentSections.actual));
      lines.push("");
      lines.push("**期望**");
      lines.push("");
      lines.push(markdownFence(bug.lastActivation?.expected || currentSections.expected));
      lines.push("");
    }
    lines.push("### 禅道完整描述");
    lines.push("");
    lines.push(markdownFence(bug.steps));
    lines.push("");
    lines.push("### 拆分字段");
    lines.push("");
    lines.push("**步骤**");
    lines.push("");
    lines.push(markdownFence(originalSections.steps));
    lines.push("");
    lines.push("**结果**");
    lines.push("");
    lines.push(markdownFence(bug.actual || originalSections.actual));
    lines.push("");
    lines.push("**期望**");
    lines.push("");
    lines.push(markdownFence(bug.expected || originalSections.expected));
    lines.push("");
    lines.push("### 附件");
    lines.push("");
    if (!attachmentLinks.length && !attachments.length) {
      lines.push("- 无");
    } else {
      if (attachmentLinks.length) {
        lines.push("链接：");
        for (const link of attachmentLinks) lines.push(`- ${oneLine(link.text)}：${link.href}`);
      }
      if (attachments.length) {
        lines.push("本地下载：");
        for (const item of attachments) lines.push(`- ${oneLine(item.name)}：${item.path || "未下载"}${item.url ? ` (${item.url})` : ""}`);
      }
    }
    lines.push("");
  }

  return lines.join("\n");
}

function ignoredItemsReport(ctx, bugs, snapshotDir) {
  const ignoredItems = bugs.filter((bug) => bug.handlingBucket !== "work");
  const lines = [];
  lines.push("# Zentao Bug Ignored Items");
  lines.push("");
  lines.push("- 用途：临时忽略/等待列表。这里放本轮不建议 Codex 直接检查或修改的 bug，并记录原因。");
  lines.push("- 规则：平台/后台、底层/硬件/驱动、缺关键日志、描述不明确、已解决/已关闭的 bug 进入这里。");
  lines.push(`- 清理：全部修完后运行 \`node "${__filename}" --cleanup "${snapshotDir}"\`，只会删除 work/ignored 临时单和 attachments/。`);
  lines.push(`- 生成时间：${new Date().toLocaleString("zh-CN", { hour12: false })}`);
  lines.push(`- 快照目录：${snapshotDir}`);
  if (ctx.repoName) lines.push(`- Worktree：${ctx.repoName}`);
  lines.push(`- Repo：${ctx.repo}`);
  lines.push(`- 分支：${ctx.branch}`);
  lines.push(`- 提交：${ctx.commit}`);
  if (ctx.projectName) lines.push(`- Zentao项目：${ctx.projectName}`);
  if (ctx.productId) lines.push(`- Zentao产品ID：${ctx.productId}`);
  if (ctx.projectId) lines.push(`- Zentao项目ID：${ctx.projectId}`);
  if (ctx.fetchMode) lines.push(`- 抓取模式：${ctx.fetchMode}`);
  lines.push(`- 忽略/等待数量：${ignoredItems.length}`);
  lines.push("");
  lines.push("| ID | 标题 | 处理 | 分类 | 原因 | 建议 |");
  lines.push("| --- | --- | --- | --- | --- | --- |");
  for (const bug of ignoredItems) {
    lines.push(`| ${bug.id} | ${(bug.title || "").replace(/\|/g, "/")} | ${bug.handlingLabel || ""} (${bug.handlingAction || ""}) | ${bug.category || ""} | ${(bug.handlingReason || "").replace(/\|/g, "/")} | ${(bug.advice || "").replace(/\|/g, "/")} |`);
  }
  lines.push("");

  for (const bug of ignoredItems) {
    const currentSections = currentSectionsForBug(bug);
    const originalSections = bug.stepSections || {};
    const attachmentLinks = bug.attachmentLinks || [];
    const attachments = bug.attachments || [];
    lines.push(`## Bug #${bug.id} ${oneLine(bug.title)}`);
    lines.push("");
    lines.push(`- 禅道链接：${bug.url}`);
    lines.push(`- 产品/项目：${oneLine(bug.product)}`);
    lines.push(`- 状态：${oneLine(bug.status)}`);
    lines.push(`- 详情状态：${bug.detailFetched ? "已打开" : "列表"}`);
    if (bug.detailFetchError) lines.push(`- 详情失败原因：${oneLine(bug.detailFetchError)}`);
    lines.push(`- 激活次数：${bug.activationCount || 0}`);
    if (bug.reactivated) {
      lines.push(`- 最后激活：${oneLine(bug.lastActivation?.date)} / ${oneLine(bug.lastActivation?.actor)} / ${oneLine(bug.lastActivation?.summary)}`);
    }
    lines.push(`- 分类/难度：${bug.category} / ${bug.difficulty}`);
    lines.push(`- Codex能否处理：${bug.canHandle}`);
    lines.push(`- 本轮处理：${bug.handlingLabel} (${bug.handlingAction})`);
    lines.push(`- 原因：${bug.handlingReason}`);
    lines.push(`- 建议：${bug.advice}`);
    lines.push("");
    if (bug.reactivated) {
      lines.push("### 当前复测失败说明（优先）");
      lines.push("");
      lines.push(markdownFence(bug.lastActivation?.note));
      lines.push("");
      lines.push("**结果**");
      lines.push("");
      lines.push(markdownFence(bug.lastActivation?.actual || currentSections.actual));
      lines.push("");
      lines.push("**期望**");
      lines.push("");
      lines.push(markdownFence(bug.lastActivation?.expected || currentSections.expected));
      lines.push("");
    }
    if (bug.detailFetched || bug.steps) {
      lines.push("### 禅道描述");
      lines.push("");
      lines.push(markdownFence(bug.steps));
      lines.push("");
      lines.push("### 拆分字段");
      lines.push("");
      lines.push("**步骤**");
      lines.push("");
      lines.push(markdownFence(originalSections.steps));
      lines.push("");
      lines.push("**结果**");
      lines.push("");
      lines.push(markdownFence(bug.actual || originalSections.actual));
      lines.push("");
      lines.push("**期望**");
      lines.push("");
      lines.push(markdownFence(bug.expected || originalSections.expected));
      lines.push("");
    }
    lines.push("### 附件");
    lines.push("");
    if (!attachmentLinks.length && !attachments.length) {
      lines.push("- 无");
    } else {
      if (attachmentLinks.length) {
        lines.push("链接：");
        for (const link of attachmentLinks) lines.push(`- ${oneLine(link.text)}：${link.href}`);
      }
      if (attachments.length) {
        lines.push("本地下载：");
        for (const item of attachments) lines.push(`- ${oneLine(item.name)}：${item.path || "未下载"}${item.url ? ` (${item.url})` : ""}`);
      }
    }
    lines.push("");
  }

  return lines.join("\n");
}

async function collectRowsFromStart(page, startUrl, args, options = {}) {
  await page.goto(startUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(800);

  const rows = [];
  if (args.ids.length) {
    for (const id of args.ids) {
      rows.push({
        id,
        href: `${SITE_URL}/bug-view-${id}.html`,
        title: "",
        rawCells: [],
      });
    }
    return rows;
  }

  const applyProjectFilter = options.applyProjectFilter !== false;
  const assignedIdSet = options.assignedIdSet instanceof Set ? options.assignedIdSet : null;
  while (rows.length < args.limit) {
    const pageRows = (await extractBugRows(page))
      .filter((row) => applyProjectFilter ? ((args.projectId || args.productId) ? true : rowMatchesFilter(row, args)) : true)
      .filter((row) => rowMatchesBugStatus(row, args))
      .filter((row) => assignedIdSet ? assignedIdSet.has(`${row.id}`) : rowMatchesAssignedTo(row, args));
    for (const r of pageRows) {
      if (!rows.find((x) => x.id === r.id)) rows.push(r);
      if (rows.length >= args.limit) break;
    }
    if (rows.length >= args.limit) break;
    const moved = await gotoNextPage(page);
    if (!moved) break;
  }
  return rows;
}

function assignedFallbackRows(rows, projectName, limit, detailLimit) {
  const matching = rows.filter((row) => projectNameMatches(row.product, projectName));
  if (matching.length) {
    return matching.slice(0, limit);
  }
  return rows.slice(0, limit);
}

async function extractBugsFromRows(page, rows, args, attachmentRoot, detailLimit) {
  const selectedRows = rows.slice(0, args.limit);
  const requestedDetailLimit = Number(args.detailLimit);
  const maxDetail = args.ids.length || !Number.isFinite(requestedDetailLimit) || requestedDetailLimit < 0
    ? selectedRows.length
    : Math.max(0, Math.min(Math.floor(requestedDetailLimit), selectedRows.length));
  const bugs = new Array(selectedRows.length);

  for (let index = maxDetail; index < selectedRows.length; index++) {
    bugs[index] = bugFromRow(selectedRows[index], args);
  }
  if (maxDetail === 0) return bugs;

  const requestedConcurrency = Number(args.detailConcurrency);
  const workerCount = Math.max(1, Math.min(
    Number.isFinite(requestedConcurrency) ? Math.floor(requestedConcurrency) : 1,
    maxDetail,
    8,
  ));
  console.log(`Deep fetching ${maxDetail} bug details with ${workerCount} parallel worker(s).`);

  let nextIndex = 0;
  const context = page.context();
  const worker = async () => {
    const workerPage = await context.newPage();
    try {
      while (true) {
        const index = nextIndex++;
        if (index >= maxDetail) break;

        const row = selectedRows[index];
        const bugAttachmentDir = path.join(attachmentRoot, `bug-${row.id}`);
        try {
          bugs[index] = await extractBugDetail(workerPage, row, bugAttachmentDir, args);
        } catch (error) {
          console.warn(`[zentao-bug-triage] Detail fetch failed for bug #${row.id}; using list row: ${compactError(error)}`);
          bugs[index] = bugFromDetailError(row, args, error);
        }
      }
    } finally {
      await workerPage.close();
    }
  };

  await Promise.all(Array.from({ length: workerCount }, () => worker()));
  return bugs;
}

function cleanupSnapshot(snapshotDir) {
  const root = path.resolve(os.homedir(), ".codex", "zentao-bug-triage", "snapshots");
  const target = path.resolve(snapshotDir);
  const rel = path.relative(root, target);
  if (!rel || rel.startsWith("..") || path.isAbsolute(rel)) {
    throw new Error(`Refuse cleanup outside snapshot root: ${target}`);
  }
  if (!fs.existsSync(path.join(target, "bugs.json")) && !fs.existsSync(path.join(target, "triage.md"))) {
    throw new Error(`Refuse cleanup because snapshot markers are missing: ${target}`);
  }

  const workPath = path.join(target, "work-items.md");
  const ignoredPath = path.join(target, "ignored-items.md");
  const attachmentPath = path.join(target, "attachments");
  const removed = [];
  if (fs.existsSync(workPath)) {
    fs.rmSync(workPath, { force: true });
    removed.push(workPath);
  }
  if (fs.existsSync(ignoredPath)) {
    fs.rmSync(ignoredPath, { force: true });
    removed.push(ignoredPath);
  }
  if (fs.existsSync(attachmentPath)) {
    fs.rmSync(attachmentPath, { recursive: true, force: true });
    removed.push(attachmentPath);
  }
  if (removed.length) {
    for (const item of removed) console.log(`Deleted: ${item}`);
  } else {
    console.log(`Nothing to cleanup under: ${target}`);
  }
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.cleanup) {
    cleanupSnapshot(args.cleanup);
    return;
  }
  const ctx = repoContext(args.repo);
  assertExpectedContext(ctx, args);
  if (args.expectRepoName) ctx.expectedRepoName = args.expectRepoName;
  if (args.expectBranch) ctx.expectedBranch = args.expectBranch;
  const hasExplicitProjectTarget = args.projectName || args.projectKey || args.projectId || args.productId;
  const projectResolution = (!args.assigned && !hasExplicitProjectTarget && !args.ids.length && args.currentProject)
    ? resolveCurrentProject(ctx)
    : { mode: "" };
  if (projectResolution.mode === "project") {
    args.projectName = projectResolution.projectName;
    if (projectResolution.productId) args.productId = projectResolution.productId;
    if (projectResolution.projectId) args.projectId = projectResolution.projectId;
    ctx.fetchMode = args.projectId ? "current-project" : (args.productId ? "current-product" : "current-project");
    ctx.projectName = projectResolution.projectName;
    if (projectResolution.productId) ctx.productId = projectResolution.productId;
    if (projectResolution.projectId) ctx.projectId = projectResolution.projectId;
    ctx.projectResolveReason = projectResolution.reason;
  } else if (!args.assigned && !hasExplicitProjectTarget && !args.ids.length) {
    args.assigned = true;
    ctx.fetchMode = "assigned-fallback";
    ctx.projectResolveReason = projectResolution.reason || "no explicit fetch mode";
  } else if (args.ids.length) {
    ctx.fetchMode = "ids";
  } else if (args.assigned) {
    ctx.fetchMode = "assigned";
  } else {
    ctx.fetchMode = args.projectId ? "project-id" : (args.productId ? "product-id" : (args.projectName ? "project-name" : "project-key"));
    ctx.projectName = args.projectName || args.projectKey || args.projectId;
    if (args.projectId) ctx.projectId = args.projectId;
    if (args.productId) ctx.productId = args.productId;
  }
  ctx.bugStatus = args.bugStatus;
  if (args.assignedTo) ctx.assignedToFilter = isMineAssignedFilter(args) ? "me" : args.assignedTo;

  console.log("Preflight context:");
  console.log(`  Worktree: ${ctx.repoName}`);
  console.log(`  Repo: ${ctx.repo}`);
  console.log(`  Branch: ${ctx.branch}`);
  console.log(`  Commit: ${ctx.commit}`);
  if (ctx.projectName) console.log(`  Zentao project: ${ctx.projectName}`);
  if (ctx.projectId) console.log(`  Zentao project ID: ${ctx.projectId}`);
  if (ctx.productId) console.log(`  Zentao product ID: ${ctx.productId}`);
  if (ctx.projectResolveReason) console.log(`  Project mapping: ${ctx.projectResolveReason}`);

  const stamp = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14);
  const outRoot = args.output || path.join(os.homedir(), ".codex", "zentao-bug-triage", "snapshots", `${stamp}_${slug(ctx.branch)}`);
  const attachmentRoot = path.join(outRoot, "attachments");
  fs.mkdirSync(outRoot, { recursive: true });

  const { chromium } = require("playwright");
  const credentials = loadCredential();
  let browser;
  let lastLaunchError;
  for (const launchOptions of [
    { channel: "chrome", headless: !args.headed },
    { channel: "msedge", headless: !args.headed },
    { headless: !args.headed },
  ]) {
    try {
      browser = await chromium.launch(launchOptions);
      break;
    } catch (error) {
      lastLaunchError = error;
    }
  }
  if (!browser) throw lastLaunchError;
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 } });
  const page = await context.newPage();
  try {
    await loginIfNeeded(page, credentials);
    if (args.projectName && !args.projectId && !args.productId && !args.assigned && !args.ids.length) {
      const cachedId = cachedProjectId(args.projectName);
      if (cachedId) {
        args.projectId = cachedId;
        ctx.projectId = cachedId;
        ctx.fetchMode = ctx.fetchMode === "current-project" ? "current-project-id" : "project-id";
        ctx.projectResolveReason = `${ctx.projectResolveReason || "project-name mapping"}; project id loaded from cache`;
      }
    }
    if (args.projectName && !args.projectId && !args.productId && !args.assigned && !args.ids.length) {
      args.projectId = await discoverProjectId(page, args.projectName);
      if (args.projectId) {
        ctx.projectId = args.projectId;
        ctx.fetchMode = ctx.fetchMode === "current-project" ? "current-project-id" : "project-id";
        ctx.projectResolveReason = `${ctx.projectResolveReason || "project-name mapping"}; project id discovered live`;
        writeProjectCache(args.projectName, args.projectId, "discoverProjectId");
      } else {
        ctx.projectResolveReason = `${ctx.projectResolveReason || "project-name mapping"}; project id not found, will try bug-browse then assigned fallback`;
      }
    } else if (args.projectId) {
      ctx.projectId = args.projectId;
      if (args.projectName) writeProjectCache(args.projectName, args.projectId, "explicit-or-map");
    }

    let assignedIdSet = null;
    if (!args.ids.length && isMineAssignedFilter(args)) {
      const assignedScanArgs = {
        ...args,
        assignedTo: "",
        projectName: "",
        projectKey: "",
        projectId: "",
        productId: "",
        bugStatus: "all",
        limit: Math.max(args.limit, args.assignedScanLimit || 0),
        detailLimit: 0,
      };
      const assignedRows = await collectRowsFromStart(
        page,
        `${SITE_URL}/my-work-bug-assignedTo.html`,
        assignedScanArgs,
        { applyProjectFilter: false },
      );
      assignedIdSet = new Set(assignedRows.map((row) => `${row.id}`));
      ctx.assignedScanCount = assignedIdSet.size;
      ctx.fetchMode = `${ctx.fetchMode || "current"}+mine`;
    }

    const projectBugUrl = args.projectId ? await resolveProjectBugUrl(page, args.projectId, args.bugStatus) : "";
    const productBrowseUrl = args.productId ? productBugUrl(args.productId, args.bugStatus) : "";
    const startUrl = args.ids.length
      ? `${SITE_URL}/my.html`
      : args.assigned
      ? `${SITE_URL}/my-work-bug-assignedTo.html`
      : args.projectId
      ? projectBugUrl
      : args.productId
      ? productBrowseUrl
      : `${SITE_URL}/bug-browse.html`;
    let rows = await collectRowsFromStart(page, startUrl, args, { applyProjectFilter: true, assignedIdSet });
    let assignedProjectFallback = false;
    let detailLimit = args.ids.length ? args.limit : Math.max(0, Math.min(args.detailLimit, args.limit));

    if (!args.ids.length && !args.assigned && args.projectName && rows.length === 0) {
      const assignedArgs = { ...args, projectName: "", projectKey: "", projectId: "" };
      const assignedRows = await collectRowsFromStart(
        page,
        `${SITE_URL}/my-work-bug-assignedTo.html`,
        assignedArgs,
        { applyProjectFilter: false },
      );
      rows = assignedFallbackRows(assignedRows, args.projectName, args.limit, args.detailLimit);
      assignedProjectFallback = rows.length > 0;
      if (assignedProjectFallback) {
        detailLimit = rows.length;
        ctx.fetchMode = `${ctx.fetchMode || "current-project"}-assigned-fallback`;
        ctx.projectResolveReason = `${ctx.projectResolveReason || "project-name mapping"}; project/list returned 0 rows, filtered assigned bugs by detail product`;
      }
    }

    let bugs = await extractBugsFromRows(page, rows, args, attachmentRoot, detailLimit);
    if (assignedProjectFallback) {
      bugs = bugs.filter((bug) => projectNameMatches(bug.product, args.projectName));
    }
    if (!args.ids.length && (assignedIdSet || args.assignedTo)) {
      bugs = bugs.filter((bug) => assignedIdSet ? assignedIdSet.has(`${bug.id}`) : rowMatchesAssignedTo(bug, args));
    }

    const jsonPath = path.join(outRoot, "bugs.json");
    const mdPath = path.join(outRoot, "triage.md");
    const chatMdPath = path.join(outRoot, "chat-summary.md");
    const workMdPath = path.join(outRoot, "work-items.md");
    const ignoredMdPath = path.join(outRoot, "ignored-items.md");
    fs.writeFileSync(jsonPath, JSON.stringify({ context: ctx, site: SITE_URL, args: { ...args, downloadMode: args.downloadMode }, projectResolution, bugs }, null, 2), "utf8");
    fs.writeFileSync(mdPath, markdownReport(ctx, bugs), "utf8");
    const chatSummary = chatSummaryReport(ctx, bugs, outRoot);
    fs.writeFileSync(chatMdPath, chatSummary, "utf8");
    const hasTempItems = bugs.length > 0;
    if (args.workMd && hasTempItems) {
      fs.writeFileSync(workMdPath, workItemsReport(ctx, bugs, outRoot), "utf8");
      fs.writeFileSync(ignoredMdPath, ignoredItemsReport(ctx, bugs, outRoot), "utf8");
    }

    const obsidianDir = path.join(os.homedir(), "Documents", "Obsidian", "CodexVault", "Codex", "projects", "zentao");
    if (args.writeObsidian && fs.existsSync(path.dirname(obsidianDir))) {
      fs.mkdirSync(obsidianDir, { recursive: true });
      fs.copyFileSync(mdPath, path.join(obsidianDir, `${stamp}_${slug(ctx.branch)}_triage.md`));
    }

    console.log(`Saved: ${jsonPath}`);
    console.log(`Saved: ${mdPath}`);
    console.log(`Saved: ${chatMdPath}`);
    if (args.workMd && hasTempItems) {
      console.log(`Saved: ${workMdPath}`);
      console.log(`Saved: ${ignoredMdPath}`);
    }
    if (ctx.fetchMode) console.log(`Fetch mode: ${ctx.fetchMode}${ctx.projectName ? ` (${ctx.projectName})` : ""}`);
    if (ctx.projectResolveReason) console.log(`Project mapping: ${ctx.projectResolveReason}`);
    console.log(chatSummary);
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(`[zentao-bug-triage] ${error.message}`);
  process.exit(1);
});
