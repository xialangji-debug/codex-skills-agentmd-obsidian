#!/usr/bin/env node
"use strict";

const fs = require("fs");
const Module = require("module");
const os = require("os");
const path = require("path");
const cp = require("child_process");

function ensureBundledNodeModules() {
  const bundledNodeRoot = path.resolve(path.dirname(process.execPath), "..");
  const fallbackNodeModules = path.join(
    os.homedir(),
    ".cache",
    "codex-runtimes",
    "codex-primary-runtime",
    "dependencies",
    "node",
    "node_modules",
  );
  const candidates = [
    path.join(bundledNodeRoot, "node_modules"),
    path.join(bundledNodeRoot, "node_modules", ".pnpm", "node_modules"),
    fallbackNodeModules,
    path.join(fallbackNodeModules, ".pnpm", "node_modules"),
  ].filter((candidate) => fs.existsSync(candidate));
  const existing = (process.env.NODE_PATH || "").split(path.delimiter).filter(Boolean);
  const modulePaths = [...new Set([...existing, ...candidates])];
  if (modulePaths.length) {
    process.env.NODE_PATH = modulePaths.join(path.delimiter);
    Module._initPaths();
  }
}

ensureBundledNodeModules();

const DEFAULT_SITE_URL = "http://zentao.hzyuelan.com/zentao";

const RESOLUTION_ALIASES = {
  fixed: ["fixed", "已解决", "解决", "已修复", "代码修复"],
  external: ["external", "外部原因", "平台原因", "平台侧", "平台端", "外部"],
  bydesign: ["bydesign", "设计如此"],
  duplicate: ["duplicate", "重复Bug", "重复bug", "重复"],
  notrepro: ["notrepro", "无法重现", "不能重现"],
  postponed: ["postponed", "延期处理", "延期"],
  willnotfix: ["willnotfix", "不予解决", "不解决"],
};

function parseArgs(argv) {
  const args = {
    repo: process.cwd(),
    ids: [],
    plan: "",
    resolution: "fixed",
    resolvedBuild: "",
    assignTo: "",
    comment: "",
    commentFile: "",
    output: "",
    siteUrl: DEFAULT_SITE_URL,
    headed: false,
    buildCurrentBranch: false,
    activateClosed: false,
    activateComment: "开发误关闭，按流程重新激活后改为已解决，关闭留给测试。",
    forceResolve: false,
    expectStatus: "已解决",
    submit: false,
    minimal: false,
  };

  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    const next = () => {
      if (i + 1 >= argv.length) throw new Error(`Missing value for ${a}`);
      return argv[++i];
    };

    if (a === "--repo") args.repo = next();
    else if (a === "--ids") args.ids = next().split(/[,\s]+/).filter(Boolean);
    else if (a === "--plan") args.plan = next();
    else if (a === "--resolution") args.resolution = next();
    else if (a === "--build" || a === "--resolved-build") args.resolvedBuild = next();
    else if (a === "--assign-to" || a === "--assigned-to") args.assignTo = next();
    else if (a === "--comment") args.comment = next();
    else if (a === "--comment-file") args.commentFile = next();
    else if (a === "--output") args.output = next();
    else if (a === "--site-url") args.siteUrl = next().replace(/\/$/, "");
    else if (a === "--headed") args.headed = true;
    else if (a === "--build-current-branch") args.buildCurrentBranch = true;
    else if (a === "--activate-closed") args.activateClosed = true;
    else if (a === "--activate-comment") args.activateComment = next();
    else if (a === "--force-resolve") args.forceResolve = true;
    else if (a === "--expect-status") args.expectStatus = next();
    else if (a === "--submit") args.submit = true;
    else if (a === "--minimal") args.minimal = true;
    else if (a === "--dry-run") args.submit = false;
    else if (a === "--help" || a === "-h") {
      console.log(`Usage:
  node zentao_bug_resolver.js --repo . --ids 2799,2917 --resolution fixed
  node zentao_bug_resolver.js --repo . --plan .codex\\zentao-resolve-plan.md
  node zentao_bug_resolver.js --repo . --plan .codex\\zentao-resolve-plan.md --submit

Defaults:
  Preview mode is the default. Use --submit to save Zentao forms.
  --resolution fixed maps to 已解决 and may leave comment empty.
  --resolution external maps to 外部原因 and requires --comment/plan comment.
  --build trunk maps to 主干.
  --build-current-branch uses the current git branch as the fixed build when none is set.
  --activate-closed reopens 已关闭 bugs before resolving them; never clicks 关闭.
  Assignee is preserved unless --assign-to is explicitly provided.
  --minimal is an --ids-only shortcut for fixed, empty comment, and preserved assignee.
`);
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${a}`);
    }
  }

  if (args.minimal) {
    if (args.plan) throw new Error("--minimal only supports --ids; use explicit fields in a resolve plan.");
    args.resolution = "fixed";
    args.assignTo = "";
    args.comment = "";
    args.commentFile = "";
  }

  return args;
}

function run(cmd, cwd) {
  try {
    return cp.execFileSync(cmd[0], cmd.slice(1), {
      cwd,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    return "";
  }
}

function repoContext(repo) {
  const resolvedRepo = path.resolve(repo);
  let branch = run(["git", "branch", "--show-current"], resolvedRepo);
  if (!branch) branch = "unknown";
  return {
    repo: resolvedRepo,
    branch,
    commit: run(["git", "rev-parse", "--short", "HEAD"], resolvedRepo) || "unknown",
    dirty: run(["git", "status", "--short"], resolvedRepo),
  };
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

async function loginIfNeeded(page, siteUrl, credentials) {
  await gotoWithRetry(page, `${siteUrl}/my.html`);
  const loginInput = page.locator('input[name="account"], input[name="username"], input#account').first();
  if (await loginInput.count()) {
    await loginInput.fill(credentials.username);
    await page.locator('input[name="password"], input#password, input[type="password"]').first().fill(credentials.password);
    await Promise.all([
      page.waitForLoadState("networkidle", { timeout: 60000 }).catch(() => {}),
      page.locator('button[type="submit"], #submit, input[type="submit"]').first().click(),
    ]);
  }
  if (page.url().includes("login")) {
    throw new Error("Zentao login failed. Confirm the saved username/password.");
  }
}

function normalize(value) {
  return `${value || ""}`.toLowerCase().replace(/\s+/g, "").trim();
}

function normalizeResolution(value) {
  const n = normalize(value);
  for (const [canonical, aliases] of Object.entries(RESOLUTION_ALIASES)) {
    if (aliases.some((alias) => normalize(alias) === n)) return canonical;
  }
  return `${value || ""}`.trim();
}

function readTextFile(filePath) {
  return fs.readFileSync(path.resolve(filePath), "utf8").replace(/^\uFEFF/, "");
}

function parseJsonPlan(filePath) {
  const parsed = JSON.parse(readTextFile(filePath));
  const items = Array.isArray(parsed) ? parsed : (parsed.bugs || parsed.items || []);
  return items.map((item) => ({
    id: `${item.id || item.bug || ""}`.replace(/^#/, ""),
    title: item.title || "",
    resolution: item.resolution || item.solution || "",
    resolvedBuild: item.resolvedBuild || item.build || "",
    assignTo: item.assignTo || item.assignedTo || "",
    comment: item.comment || item.remark || "",
  })).filter((item) => item.id);
}

function parseMarkdownPlan(filePath) {
  const text = readTextFile(filePath);
  const matches = Array.from(text.matchAll(/^##\s+Bug\s+#?(\d+)\s*(.*?)\s*$/gim));
  const items = [];

  for (let index = 0; index < matches.length; index++) {
    const match = matches[index];
    const start = match.index + match[0].length;
    const end = index + 1 < matches.length ? matches[index + 1].index : text.length;
    const section = text.slice(start, end).replace(/^\r?\n/, "");
    const item = { id: match[1], title: match[2].trim(), resolution: "", resolvedBuild: "", assignTo: "", comment: "" };
    const lines = section.split(/\r?\n/);
    let commentStart = -1;

    for (let i = 0; i < lines.length; i++) {
      const kv = lines[i].match(/^\s*-?\s*([^:：]+)\s*[:：]\s*(.*)$/);
      if (!kv) continue;
      const key = normalize(kv[1]);
      const value = kv[2].trim();
      if (["resolution", "解决方案", "solution"].includes(key)) item.resolution = value;
      else if (["resolvedbuild", "build", "解决版本"].includes(key)) item.resolvedBuild = value;
      else if (["assignto", "assignedto", "指派给"].includes(key)) item.assignTo = value;
      else if (["comment", "remark", "备注"].includes(key)) {
        commentStart = i;
        item.comment = value;
        break;
      }
    }

    if (commentStart >= 0) {
      const first = item.comment;
      const rest = lines.slice(commentStart + 1).join("\n").trim();
      item.comment = [first, rest].filter(Boolean).join(first && rest ? "\n" : "");
    }
    items.push(item);
  }

  return items;
}

function loadPlan(args) {
  if (args.plan) {
    const ext = path.extname(args.plan).toLowerCase();
    const items = ext === ".json" ? parseJsonPlan(args.plan) : parseMarkdownPlan(args.plan);
    if (!items.length) throw new Error(`No bug items found in plan: ${args.plan}`);
    return items;
  }

  if (!args.ids.length) throw new Error("Pass --ids or --plan.");
  let comment = args.comment;
  if (args.commentFile) comment = readTextFile(args.commentFile).trim();
  return args.ids.map((id) => ({
    id,
    title: "",
    resolution: args.resolution,
    resolvedBuild: args.resolvedBuild,
    assignTo: args.assignTo,
    comment,
  }));
}

function resolveBuildAlias(value, ctx) {
  const n = normalize(value);
  if (["currentbranch", "current-branch", "branch", "当前分支", "当前版本"].includes(n)) return ctx.branch;
  return value;
}

function validateItems(items, defaults, ctx) {
  for (const item of items) {
    item.id = `${item.id || ""}`.trim().replace(/^#/, "");
    item.resolution = normalizeResolution(item.resolution || defaults.resolution || "fixed");
    item.resolvedBuild = resolveBuildAlias(`${item.resolvedBuild || defaults.resolvedBuild || ""}`.trim(), ctx);
    item.assignTo = `${item.assignTo || defaults.assignTo || ""}`.trim();
    item.comment = `${item.comment || ""}`.trim();

    if (!/^\d+$/.test(item.id)) throw new Error(`Invalid bug id: ${item.id}`);
    if (item.resolution === "external" && !item.comment) {
      throw new Error(`Bug #${item.id} uses 外部原因/external but comment is empty.`);
    }
    if (item.resolution !== "fixed" && item.resolution !== "external" && !item.comment) {
      throw new Error(`Bug #${item.id} uses ${item.resolution}; add a comment or use fixed.`);
    }
    if (item.resolution === "fixed" && !item.resolvedBuild) {
      item.resolvedBuild = defaults.buildCurrentBranch ? ctx.branch : "trunk";
    }
  }
}

async function gotoWithRetry(page, url, attempts = 3) {
  let lastError;
  for (let attempt = 1; attempt <= attempts; attempt++) {
    try {
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
      return;
    } catch (error) {
      lastError = error;
      if (attempt === attempts) break;
      console.warn(`Navigation failed (${attempt}/${attempts}), retrying: ${url}`);
      await page.waitForTimeout(750 * attempt);
    }
  }
  throw lastError;
}

async function findFormFrame(page) {
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) {
    for (const frame of page.frames()) {
      if (await frame.locator('input[name="resolution"]').count().catch(() => 0)) return frame;
    }
    await page.waitForTimeout(300);
  }
  throw new Error("Resolve form not found.");
}

async function gotoResolveForm(page, siteUrl, bugId) {
  await gotoWithRetry(page, `${siteUrl}/bug-resolve-${bugId}.html`);
  await page.waitForTimeout(1000);
  return findFormFrame(page);
}

async function findGenericFormFrame(page, markerText) {
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) {
    for (const frame of page.frames()) {
      const found = await frame.evaluate((marker) => {
        const text = document.body?.innerText || "";
        return text.includes(marker) && !!document.querySelector("form");
      }, markerText).catch(() => false);
      if (found) return frame;
    }
    await page.waitForTimeout(300);
  }
  throw new Error(`${markerText} form not found.`);
}

async function gotoActivateForm(page, siteUrl, bugId) {
  await gotoWithRetry(page, `${siteUrl}/bug-activate-${bugId}.html`);
  await page.waitForTimeout(1000);
  return findGenericFormFrame(page, "激活Bug");
}

async function readFormState(frame) {
  return await frame.evaluate(() => {
    const parsePicker = (name) => {
      for (const node of document.querySelectorAll("[zui-create-picker]")) {
        try {
          const cfg = JSON.parse(node.getAttribute("zui-create-picker"));
          if (cfg.name === name) return Array.isArray(cfg.items) ? cfg.items : [];
        } catch {
          // Ignore non-JSON picker definitions.
        }
      }
      return [];
    };
    const text = document.body?.innerText || "";
    const lines = text.split(/\n/).map((line) => line.trim()).filter(Boolean);
    const resolveIndex = lines.findIndex((line) => line === "解决Bug");
    let titleLine = "";
    if (resolveIndex >= 0) {
      titleLine = lines.slice(resolveIndex + 1).find((line) => !/^\d+$/.test(line)) || "";
    }
    if (!titleLine) {
      const nav = new Set(["测试", "仪表盘", "Bug", "用例", "套件", "测试单", "测试报告", "用例库", "保存", "返回"]);
      titleLine = lines.find((line) => !nav.has(line) && !/^\d+$/.test(line)) || "";
    }
    const values = {};
    for (const name of ["resolution", "resolvedBuild", "assignedTo"]) {
      values[name] = document.querySelector(`input[name="${name}"]`)?.value || "";
    }
    return {
      title: titleLine.trim(),
      resolutionOptions: parsePicker("resolution"),
      buildOptions: parsePicker("resolvedBuild"),
      assignOptions: parsePicker("assignedTo"),
      values,
    };
  });
}

function pickOption(items, requested, fieldName) {
  const value = `${requested || ""}`.trim();
  if (!value) return { value: "", label: "" };
  if (fieldName === "assignedTo" && ["self", "current", "me", "自己"].includes(normalize(value))) {
    const first = items.find((item) => item.value);
    if (first) return { value: first.value, label: first.text || first.value };
    return { value: "", label: "" };
  }

  const n = normalize(value);
  const exact = items.find((item) => normalize(item.value) === n || normalize(item.text) === n);
  if (exact) return { value: exact.value, label: exact.text || exact.value };

  const partial = items.find((item) => normalize(item.text).includes(n) || normalize(item.keys).includes(n));
  if (partial) return { value: partial.value, label: partial.text || partial.value };

  if (fieldName === "resolvedBuild" && ["trunk", "主干"].includes(n)) {
    const trunk = items.find((item) => item.value === "trunk" || item.text === "主干");
    if (trunk) return { value: trunk.value, label: trunk.text || trunk.value };
  }

  const available = items.map((item) => `${item.text || item.value}=${item.value}`).filter(Boolean).slice(0, 12).join(", ");
  throw new Error(`Cannot find ${fieldName} option "${value}". Available: ${available}`);
}

async function setPickerValue(frame, name, value) {
  return await frame.evaluate(({ name, value }) => {
    const input = document.querySelector(`input[name="${name}"]`);
    if (!input) throw new Error(`Missing input[name="${name}"]`);
    input.value = value || "";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    try {
      const picker = window.$(input).zui("picker");
      if (picker?.$?.setValue) picker.$.setValue(value || "");
    } catch {
      // Hidden input value is enough for form submission.
    }
    return input.value;
  }, { name, value });
}

async function fillComment(page, frame, comment) {
  if (!comment) return "";
  const editor = frame.locator('zen-editor[name="comment"]').first();
  if (await editor.count()) {
    const editable = editor.locator('[contenteditable="true"], textarea').first();
    if (await editable.count()) {
      await editable.fill(comment);
      await editable.evaluate((node) => node.blur()).catch(() => {});
    } else {
      await editor.evaluate((node, value) => {
        node.value = value;
        node.setAttribute("value", value);
        node.dispatchEvent(new Event("input", { bubbles: true, composed: true }));
        node.dispatchEvent(new Event("change", { bubbles: true, composed: true }));
      }, comment);
    }
  } else {
    const textarea = frame.locator('textarea[name="comment"], textarea').first();
    if (await textarea.count()) await textarea.fill(comment);
  }

  await page.waitForTimeout(200);

  const postedComment = await frame.evaluate(() => {
    const form = document.querySelector("form");
    if (!form) return "";
    const values = Array.from(new FormData(form).entries()).filter(([key]) => key === "comment");
    return `${values[0]?.[1] || ""}`;
  });
  if (!postedComment.trim()) {
    throw new Error("Comment field did not stick in the Zentao resolve form.");
  }
  return postedComment;
}

function pickBuildOption(items, requested) {
  try {
    return pickOption(items, requested || "trunk", "resolvedBuild");
  } catch (error) {
    if (["trunk", "主干"].includes(normalize(requested))) throw error;
    const fallback = pickOption(items, "trunk", "resolvedBuild");
    return { ...fallback, fallbackFrom: requested };
  }
}

async function formDataSnapshot(frame) {
  return await frame.evaluate(() => {
    const form = document.querySelector("form");
    if (!form) return [];
    return Array.from(new FormData(form).entries()).map(([key, value]) => [
      key,
      value instanceof File ? value.name : `${value}`,
    ]);
  });
}

async function submitForm(page, frame) {
  await Promise.all([
    page.waitForLoadState("networkidle", { timeout: 60000 }).catch(() => {}),
    frame.locator('button[type="submit"], button:has-text("保存")').first().click({ timeout: 10000 }),
  ]);
  await page.waitForTimeout(2500);
}

async function readBugInfo(page, siteUrl, bugId) {
  await gotoWithRetry(page, `${siteUrl}/bug-view-${bugId}.html`);
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    for (const frame of page.frames()) {
      const info = await frame.evaluate((id) => {
        const text = document.body?.innerText || "";
        const match = text.match(/Bug状态\s*\n\s*([^\n]+)/);
        const lines = text.split(/\n/).map((line) => line.trim()).filter(Boolean);
        const idIndex = lines.indexOf(String(id));
        return {
          status: match ? match[1].trim() : "",
          title: idIndex >= 0 ? (lines[idIndex + 1] || "") : "",
        };
      }, `${bugId}`).catch(() => ({ status: "", title: "" }));
      if (info.status) return info;
    }
    await page.waitForTimeout(500);
  }
  return { status: "", title: "" };
}

async function readBugStatus(page, siteUrl, bugId) {
  return (await readBugInfo(page, siteUrl, bugId)).status;
}

async function activateBug(page, args, item) {
  const frame = await gotoActivateForm(page, args.siteUrl, item.id);
  const postedComment = await fillComment(page, frame, args.activateComment);
  await submitForm(page, frame);
  const status = await readBugStatus(page, args.siteUrl, item.id);
  if (status !== "激活") {
    throw new Error(`Bug #${item.id} activation failed; status is "${status}".`);
  }
  return { status, postedCommentLength: postedComment.length };
}

function formValue(formData, key) {
  const hit = formData.find(([name]) => name === key);
  return hit ? hit[1] : "";
}

async function processBug(page, args, item) {
  const beforeInfo = await readBugInfo(page, args.siteUrl, item.id);
  let activated = false;
  let activationPlanned = false;
  let activationCommentLength = 0;
  let skipped = false;
  let skipReason = "";

  if (beforeInfo.status === "已关闭") {
    if (!args.activateClosed) {
      throw new Error(`Bug #${item.id} is 已关闭. Pass --activate-closed to reopen it before resolving; do not click 关闭 from development.`);
    }
    if (!args.submit) {
      activationPlanned = true;
      skipped = true;
      skipReason = "dry-run: closed bug would be activated then resolved with --submit";
      return {
        id: item.id,
        title: item.title || beforeInfo.title,
        requestedResolution: item.resolution,
        resolution: { value: item.resolution, label: item.resolution },
        build: { value: item.resolvedBuild, label: item.resolvedBuild },
        assignee: { value: item.assignTo, label: item.assignTo, preserved: !item.assignTo },
        beforeStatus: beforeInfo.status,
        activated,
        activationPlanned,
        activationCommentLength,
        skipped,
        skipReason,
        commentEmpty: !item.comment,
        postedCommentLength: 0,
        submitted: false,
        finalStatus: beforeInfo.status,
        formData: [],
      };
    }
    const activation = await activateBug(page, args, item);
    activated = true;
    activationCommentLength = activation.postedCommentLength;
  }

  if (beforeInfo.status === "已解决" && !args.forceResolve) {
    skipped = true;
    skipReason = "already-resolved";
    return {
      id: item.id,
      title: item.title || beforeInfo.title,
      requestedResolution: item.resolution,
      resolution: { value: item.resolution, label: item.resolution },
      build: { value: item.resolvedBuild, label: item.resolvedBuild },
      assignee: { value: item.assignTo, label: item.assignTo, preserved: !item.assignTo },
      beforeStatus: beforeInfo.status,
      activated,
      activationPlanned,
      activationCommentLength,
      skipped,
      skipReason,
      commentEmpty: !item.comment,
      postedCommentLength: 0,
      submitted: false,
      finalStatus: beforeInfo.status,
      formData: [],
    };
  }

  const frame = await gotoResolveForm(page, args.siteUrl, item.id);
  const state = await readFormState(frame);

  const resolution = pickOption(state.resolutionOptions, item.resolution, "resolution");
  const build = item.resolution === "fixed"
    ? pickBuildOption(state.buildOptions, item.resolvedBuild || "trunk")
    : (item.resolvedBuild ? pickOption(state.buildOptions, item.resolvedBuild, "resolvedBuild") : { value: "", label: "" });
  const assignee = item.assignTo
    ? pickOption(state.assignOptions, item.assignTo, "assignedTo")
    : {
        value: state.values.assignedTo,
        label: state.assignOptions.find((option) => option.value === state.values.assignedTo)?.text || state.values.assignedTo,
        preserved: true,
      };

  await setPickerValue(frame, "resolution", resolution.value);
  if (build.value) await setPickerValue(frame, "resolvedBuild", build.value);
  if (assignee.value) await setPickerValue(frame, "assignedTo", assignee.value);
  const postedComment = await fillComment(page, frame, item.comment);
  const formData = await formDataSnapshot(frame);
  const submittedResolution = formValue(formData, "resolution");
  const submittedBuild = formValue(formData, "resolvedBuild");
  if (resolution.value && submittedResolution !== resolution.value) {
    throw new Error(`Bug #${item.id} resolution field did not stick: expected ${resolution.value}, got ${submittedResolution}`);
  }
  if (item.resolution === "fixed" && build.value && submittedBuild !== build.value) {
    throw new Error(`Bug #${item.id} resolvedBuild field did not stick: expected ${build.value}, got ${submittedBuild}`);
  }

  let submitted = false;
  let finalStatus = "";
  if (args.submit) {
    await submitForm(page, frame);
    submitted = true;
    finalStatus = await readBugStatus(page, args.siteUrl, item.id);
    if (item.resolution === "fixed" && args.expectStatus && finalStatus !== args.expectStatus) {
      throw new Error(`Bug #${item.id} submit did not reach ${args.expectStatus}; final status is "${finalStatus}".`);
    }
  }

  return {
    id: item.id,
    title: item.title || state.title || beforeInfo.title,
    requestedResolution: item.resolution,
    resolution,
    build,
    assignee,
    beforeStatus: beforeInfo.status,
    activated,
    activationPlanned,
    activationCommentLength,
    skipped,
    skipReason,
    commentEmpty: !item.comment,
    postedCommentLength: postedComment.length,
    submitted,
    finalStatus,
    formData,
  };
}

function ensureOutputDir(args, ctx, items) {
  if (args.output) {
    fs.mkdirSync(args.output, { recursive: true });
    return path.resolve(args.output);
  }
  const stamp = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14);
  const ids = items.map((item) => item.id).join("-");
  const safeBranch = (ctx.branch || "unknown").replace(/[^\w.-]+/g, "_").slice(0, 80);
  const outDir = path.join(os.homedir(), ".codex", "zentao-bug-resolver", "runs", `${stamp}_${safeBranch}_${ids}`);
  fs.mkdirSync(outDir, { recursive: true });
  return outDir;
}

function markdownReport(ctx, args, results) {
  const lines = [];
  lines.push("# Zentao Resolve Report");
  lines.push("");
  lines.push(`- Mode: ${args.submit ? "submit" : "dry-run"}`);
  lines.push(`- Repo: ${ctx.repo}`);
  lines.push(`- Branch: ${ctx.branch}`);
  lines.push(`- Commit: ${ctx.commit}`);
  lines.push("");
  lines.push("| ID | Title | Before | Solution | Build | Assign To | Activated | Comment | Submitted | Final Status |");
  lines.push("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |");
  for (const r of results) {
    const title = (r.title || "").replace(/\|/g, "/");
    const solution = `${r.resolution.label || r.resolution.value} (${r.resolution.value})`;
    const fallback = r.build.fallbackFrom ? `, fallback from ${r.build.fallbackFrom}` : "";
    const build = r.build.value ? `${r.build.label || r.build.value} (${r.build.value}${fallback})` : "-";
    const assignee = r.assignee.preserved ? "preserved" : (r.assignee.value ? `${r.assignee.label || r.assignee.value} (${r.assignee.value})` : "-");
    const activated = r.activated ? "yes" : (r.activationPlanned ? "planned" : "no");
    const comment = r.commentEmpty ? "empty" : `${r.postedCommentLength} chars`;
    const status = r.skipped ? `${r.finalStatus || "-"} (${r.skipReason})` : (r.finalStatus || "-");
    lines.push(`| ${r.id} | ${title} | ${r.beforeStatus || "-"} | ${solution} | ${build} | ${assignee} | ${activated} | ${comment} | ${r.submitted ? "yes" : "no"} | ${status} |`);
  }
  lines.push("");
  return lines.join("\n");
}

async function main() {
  const args = parseArgs(process.argv);
  const ctx = repoContext(args.repo);
  const items = loadPlan(args);
  validateItems(items, args, ctx);
  const outDir = ensureOutputDir(args, ctx, items);

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

  const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
  const results = [];
  try {
    await loginIfNeeded(page, args.siteUrl, credentials);
    for (const item of items) {
      console.log(`${args.submit ? "Submitting" : "Previewing"} Bug #${item.id} (${item.resolution})`);
      results.push(await processBug(page, args, item));
    }
  } finally {
    await browser.close();
  }

  const jsonPath = path.join(outDir, "resolve-report.json");
  const mdPath = path.join(outDir, "resolve-report.md");
  fs.writeFileSync(jsonPath, JSON.stringify({ context: ctx, mode: args.submit ? "submit" : "dry-run", site: args.siteUrl, items, results }, null, 2), "utf8");
  fs.writeFileSync(mdPath, markdownReport(ctx, args, results), "utf8");

  console.log(`Saved: ${jsonPath}`);
  console.log(`Saved: ${mdPath}`);
  console.log(markdownReport(ctx, args, results));
}

if (require.main === module) {
  main().catch((error) => {
    console.error(`[zentao-bug-resolver] ${error.message}`);
    process.exit(1);
  });
}

module.exports = {
  parseArgs,
  parseJsonPlan,
  parseMarkdownPlan,
  pickBuildOption,
};
