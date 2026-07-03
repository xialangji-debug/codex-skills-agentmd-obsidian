#!/usr/bin/env node
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync, spawnSync } = require("child_process");

const SITE_URL = "https://fnos.yuelaniot.com:5667";
const DEFAULT_TEAM = "阿科奇";
const DEFAULT_DOMESTIC = "阿科奇-国内";
const OVERWRITE_KEEP_NAME = 3;

function printUsage() {
  console.log(`Usage:
  node fnos_upload_release.js --repo D:\\XM\\c10lezhi [options]

Options:
  --repo <path>                   Repo root. Default: current working directory.
  --release-time <YYYYMMDD_HHMM>  Remote release folder. Default: timestamp in yl_device_ver.
  --upload-dir <path>             Local upload directory. Default: out/product/craneg_modem_watch/release_upload/<time>.
  --file <path>                   Explicit file to upload. Can be repeated.
  --readme <path>                 User-provided readme.txt to upload.
  --include-readme                Include <upload-dir>/readme.txt if present.
  --remote-product-folder <name>  Product folder under 阿科奇-国内. Default: project-folder-map.md or heuristic.
  --create-missing-folder         Deprecated alias; timestamp folders are created automatically for real uploads.
  --no-create-missing-folder      Refuse to create a missing timestamp release folder.
  --preflight                     Check login, product folder, release folder, and remote name collisions without local files.
  --dry-run                       Resolve paths and collisions, but do not upload.
  --headed                        Show browser window for debugging.
  --replace-existing              Allow replacing existing remote same-name files. Use only after user approval.
  --allow-existing-identical      Treat existing remote files with the same names and sizes as already uploaded.
  --help                          Show this help.

Examples:
  node fnos_upload_release.js --repo . --dry-run
  node fnos_upload_release.js --repo . --release-time 20260702_1726
`);
}

function fail(message) {
  console.error(`ERROR: ${message}`);
  process.exit(1);
}

function parseArgs(argv) {
  const args = {
    repo: process.cwd(),
    files: [],
    dryRun: false,
    headed: false,
    replaceExisting: false,
    allowExistingIdentical: false,
    includeReadme: false,
    preflight: false,
    createMissingFolder: true,
  };
  for (let i = 2; i < argv.length; i++) {
    const item = argv[i];
    const next = () => {
      if (i + 1 >= argv.length) fail(`Missing value for ${item}`);
      return argv[++i];
    };
    switch (item) {
      case "--help":
      case "-h":
        printUsage();
        process.exit(0);
        break;
      case "--repo":
        args.repo = next();
        break;
      case "--release-time":
        args.releaseTime = next();
        break;
      case "--upload-dir":
        args.uploadDir = next();
        break;
      case "--file":
        args.files.push(next());
        break;
      case "--readme":
        args.readme = next();
        break;
      case "--remote-product-folder":
        args.remoteProductFolder = next();
        break;
      case "--create-missing-folder":
        args.createMissingFolder = true;
        break;
      case "--no-create-missing-folder":
        args.createMissingFolder = false;
        break;
      case "--preflight":
        args.preflight = true;
        args.dryRun = true;
        break;
      case "--dry-run":
        args.dryRun = true;
        break;
      case "--headed":
        args.headed = true;
        break;
      case "--replace-existing":
        args.replaceExisting = true;
        break;
      case "--allow-existing-identical":
        args.allowExistingIdentical = true;
        break;
      case "--include-readme":
        args.includeReadme = true;
        break;
      default:
        fail(`Unknown option: ${item}`);
    }
  }
  return args;
}

function requirePlaywright() {
  try {
    return require("playwright");
  } catch (_) {
    const bundled = path.join(
      os.homedir(),
      ".cache",
      "codex-runtimes",
      "codex-primary-runtime",
      "dependencies",
      "node",
      "node_modules",
      "playwright"
    );
    try {
      return require(bundled);
    } catch (error) {
      fail(`Cannot load Playwright. Tried normal require and ${bundled}. ${error.message}`);
    }
  }
}

function existingBrowserPath() {
  const candidates = [
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ];
  return candidates.find((item) => fs.existsSync(item));
}

function runGit(repo, args) {
  const result = spawnSync("git", args, { cwd: repo, encoding: "utf8" });
  if (result.status !== 0) return "";
  return result.stdout.trim();
}

function readTextMaybe(file) {
  if (!fs.existsSync(file)) return "";
  return fs.readFileSync(file, "utf8");
}

function extractDeviceVer(repo) {
  const ylH = path.join(repo, "gui", "lv_watch", "lv_apps", "yl", "yl.h");
  const text = readTextMaybe(ylH);
  const match = text.match(/#define\s+yl_device_ver\s+"([^"]+)"/);
  if (!match) fail(`Could not find yl_device_ver in ${ylH}`);
  const timestamp = match[1].match(/_(\d{8}_\d{4})_/);
  if (!timestamp) fail(`Could not find release timestamp in yl_device_ver: ${match[1]}`);
  return { ylH, deviceVer: match[1], releaseTime: timestamp[1] };
}

function deviceVerForReleaseTime(deviceVer, releaseTime) {
  const next = deviceVer.replace(/_(\d{8}_\d{4})_/, `_${releaseTime}_`);
  if (next === deviceVer && !deviceVer.includes(`_${releaseTime}_`)) {
    fail(`Could not replace release timestamp in yl_device_ver: ${deviceVer}`);
  }
  return next;
}

function normalizeName(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[\\/\s_\-()（）]+/g, "");
}

function isSameName(a, b) {
  return normalizeName(a) === normalizeName(b);
}

function parseProjectFolderMap(skillDir) {
  const file = path.join(skillDir, "references", "project-folder-map.md");
  const text = readTextMaybe(file);
  const blocks = [];
  for (const match of text.matchAll(/```text\s*([\s\S]*?)```/g)) {
    const block = {};
    for (const line of match[1].split(/\r?\n/)) {
      const pair = line.match(/^\s*([a-zA-Z_]+):\s*(.*?)\s*$/);
      if (pair) block[pair[1]] = pair[2];
    }
    if (block.fnos_folder) blocks.push(block);
  }
  return blocks;
}

function localPathMatches(rulePath, repo) {
  if (!rulePath) return true;
  const parts = rulePath.split(/\s+or\s+/i).map((item) => path.resolve(item.trim()).toLowerCase());
  const resolvedRepo = path.resolve(repo).toLowerCase();
  return parts.some((item) => resolvedRepo === item || resolvedRepo.startsWith(item + path.sep));
}

function chooseMappedProductFolder({ repo, branch, deviceVer, explicitFolder, skillDir }) {
  if (explicitFolder) return { folder: explicitFolder, source: "cli" };
  const matches = parseProjectFolderMap(skillDir)
    .filter((item) => localPathMatches(item.local_path, repo))
    .filter((item) => !item.branch_contains || branch.includes(item.branch_contains))
    .filter((item) => !item.yl_device_ver_contains || deviceVer.includes(item.yl_device_ver_contains));
  if (matches.length === 1) {
    return { folder: matches[0].fnos_folder, source: "project-folder-map.md" };
  }
  if (matches.length > 1) {
    matches.sort((a, b) => {
      const aScore = (a.branch_contains || "").length + (a.yl_device_ver_contains || "").length;
      const bScore = (b.branch_contains || "").length + (b.yl_device_ver_contains || "").length;
      return bScore - aScore;
    });
    if (matches[0].fnos_folder !== matches[1].fnos_folder) {
      fail(`Multiple remote product mappings matched. Pass --remote-product-folder.\n${matches.map((m) => `  ${m.fnos_folder}`).join("\n")}`);
    }
    return { folder: matches[0].fnos_folder, source: "project-folder-map.md" };
  }
  return { folder: "", source: "heuristic" };
}

function heuristicProductFolder(deviceVer, branch, candidates) {
  const ver = deviceVer.toUpperCase();
  const branchText = branch.toUpperCase();
  const tokens = [];
  for (const token of ["TW10", "TW18", "C10", "JC2", "JC8", "LT52", "LINKI", "L1"]) {
    if (ver.includes(token) || branchText.includes(token)) tokens.push(token);
  }
  const semantic = [
    ["LZ", "乐智"],
    ["DQ", "定乾"],
    ["XCX", "小程序"],
    ["APP", "APP"],
    ["GB", "公版"],
    ["PUBLIC", "公版"],
  ];
  for (const [needle, label] of semantic) {
    if (ver.includes(`_${needle}_`) || branchText.includes(needle)) tokens.push(label);
  }

  const scored = candidates.map((item) => {
    const normalized = normalizeName(item.name);
    let score = 0;
    for (const token of tokens) {
      if (normalized.includes(normalizeName(token))) score += token.length >= 4 ? 3 : 2;
    }
    return { name: item.name, score };
  }).sort((a, b) => b.score - a.score || a.name.localeCompare(b.name, "zh"));

  if (scored.length && scored[0].score > 0 && (!scored[1] || scored[0].score > scored[1].score)) {
    return scored[0].name;
  }
  fail(`Could not uniquely choose remote product folder. Pass --remote-product-folder.\nCandidates:\n${candidates.map((c) => `  ${c.name}`).join("\n")}`);
}

function fileInfo(file) {
  const stat = fs.statSync(file);
  return {
    path: path.resolve(file),
    name: path.basename(file),
    size: stat.size,
    mtimeMs: stat.mtimeMs,
  };
}

function chooseLocalFiles(args, repo, deviceVer, releaseTime) {
  const explicit = args.files.map((item) => path.resolve(item));
  if (args.readme) explicit.push(path.resolve(args.readme));
  if (explicit.length) {
    for (const file of explicit) {
      if (!fs.existsSync(file) || !fs.statSync(file).isFile()) fail(`Local upload file does not exist: ${file}`);
    }
    return explicit.map(fileInfo);
  }

  const uploadDir = path.resolve(args.uploadDir || path.join(repo, "out", "product", "craneg_modem_watch", "release_upload", releaseTime));
  if (!fs.existsSync(uploadDir) || !fs.statSync(uploadDir).isDirectory()) {
    fail(`Local upload directory does not exist: ${uploadDir}`);
  }
  const expectedZip = path.join(uploadDir, `${deviceVer}.zip`);
  const expectedMdb = path.join(uploadDir, `${deviceVer}.mdb.txt`);
  const files = [];
  if (fs.existsSync(expectedZip)) files.push(expectedZip);
  if (fs.existsSync(expectedMdb)) files.push(expectedMdb);

  if (files.length < 2) {
    const entries = fs.readdirSync(uploadDir).map((name) => path.join(uploadDir, name));
    const zips = entries.filter((item) => item.toLowerCase().endsWith(".zip") && !item.toLowerCase().includes("source"));
    const mdbs = entries.filter((item) => item.toLowerCase().endsWith(".mdb.txt"));
    if (!files.some((item) => item.endsWith(".zip")) && zips.length === 1) files.push(zips[0]);
    if (!files.some((item) => item.endsWith(".mdb.txt")) && mdbs.length === 1) files.push(mdbs[0]);
  }

  if (!files.some((item) => item.toLowerCase().endsWith(".zip"))) fail(`Could not choose firmware zip in ${uploadDir}`);
  if (!files.some((item) => item.toLowerCase().endsWith(".mdb.txt"))) fail(`Could not choose mdb txt in ${uploadDir}`);

  const readme = path.join(uploadDir, "readme.txt");
  if (args.includeReadme) {
    if (!fs.existsSync(readme)) fail(`--include-readme was passed, but readme.txt is missing: ${readme}`);
    files.push(readme);
  }
  return files.map(fileInfo);
}

function expectedRemoteFiles(args, deviceVer) {
  const files = [
    { name: `${deviceVer}.zip`, size: null, preflight: true },
    { name: `${deviceVer}.mdb.txt`, size: null, preflight: true },
  ];
  if (args.readme || args.includeReadme) {
    files.push({ name: "readme.txt", size: null, preflight: true });
  }
  return files;
}

function loadCredentials() {
  if (process.env.FNOS_USER && process.env.FNOS_PASS) {
    return { username: process.env.FNOS_USER, password: process.env.FNOS_PASS };
  }
  const credentialPath = path.join(os.homedir(), ".codex", "secrets", "akq-firmware-release", "fnos.credential.xml");
  if (!fs.existsSync(credentialPath)) {
    fail(`Missing saved fnOS credential: ${credentialPath}`);
  }
  const command = [
    "$ErrorActionPreference='Stop'",
    `$cred = Import-Clixml -LiteralPath ${JSON.stringify(credentialPath)}`,
    "$obj = @{ username = $cred.UserName; password = $cred.GetNetworkCredential().Password }",
    "$obj | ConvertTo-Json -Compress",
  ].join("; ");
  try {
    const stdout = execFileSync("powershell.exe", ["-NoProfile", "-Command", command], { encoding: "utf8" });
    const parsed = JSON.parse(stdout);
    if (!parsed.username || !parsed.password) fail("Saved fnOS credential is empty");
    return { username: parsed.username, password: parsed.password };
  } catch (error) {
    fail(`Could not load saved fnOS credential: ${error.message}`);
  }
}

async function login(page, credentials) {
  await page.goto(`${SITE_URL}/login`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForSelector('input[name="username"], input[placeholder="用户名"]', { timeout: 60000 });
  await page.fill('input[name="username"], input[placeholder="用户名"]', credentials.username);
  await page.fill('input[name="password"], input[placeholder="密码"]', credentials.password);
  await Promise.all([
    page.click('button[type="submit"], button:has-text("登录")'),
    page.waitForTimeout(8000),
  ]);
  const loginState = await page.evaluate(async () => {
    const mod = await import("/assets/index-CMZOY5-G.js");
    return { url: location.href, tokenPresent: !!mod.aY?.() };
  }).catch(() => ({ url: page.url(), tokenPresent: false }));
  if (loginState.url.includes("/login") || !loginState.tokenPresent) {
    fail("fnOS login failed with saved credentials. Please confirm the password.");
  }
}

async function pageCollectFiles(page, remotePath, teamRoot = false) {
  return page.evaluate(async ({ remotePath, teamRoot }) => {
    const mod = await import("/assets/index-CMZOY5-G.js");
    const api = mod.d;
    function collectFiles(promise) {
      return new Promise((resolve, reject) => {
        const files = [];
        const observable = promise.createObservable();
        const timer = setTimeout(() => reject({ timeout: true, files }), 30000);
        observable.subscribe((ev) => {
          if (ev.files) files.push(...ev.files);
          if (ev.result && ev.result !== "doing") {
            clearTimeout(timer);
            ev.result === "succ" ? resolve(files) : reject(ev);
          }
        });
      });
    }
    if (teamRoot) {
      return collectFiles(api.file.teamLsDir()).then((files) =>
        files.map((item) => ({ ...item, path: `vol${item.v}/@team/${item.name}` }))
      );
    }
    return collectFiles(api.file.ls({ path: remotePath }));
  }, { remotePath, teamRoot });
}

async function pageCanListFolder(page, remotePath) {
  try {
    await pageCollectFiles(page, remotePath);
    return true;
  } catch (_) {
    return false;
  }
}

async function pageMkdir(page, remotePath) {
  return page.evaluate(async ({ remotePath }) => {
    const mod = await import("/assets/index-CMZOY5-G.js");
    return mod.d.file.mkdir({ path: remotePath });
  }, { remotePath });
}

function findByName(items, name) {
  return items.find((item) => item.name === name) || items.find((item) => isSameName(item.name, name));
}

async function recursiveFindFolder(page, rootPath, targetName, maxDepth) {
  const found = [];
  async function visit(currentPath, depth) {
    if (depth > maxDepth) return;
    const children = await pageCollectFiles(page, currentPath);
    for (const child of children.filter((item) => item.dir === 1)) {
      const childPath = `${currentPath}/${child.name}`;
      if (isSameName(child.name, targetName)) found.push({ ...child, path: childPath });
      await visit(childPath, depth + 1);
    }
  }
  await visit(rootPath, 1);
  return found;
}

async function resolveRemoteTarget(page, { productFolder, releaseTime, deviceVer, branch, createMissingFolder, dryRun }) {
  const teams = await pageCollectFiles(page, "", true);
  const team = findByName(teams, DEFAULT_TEAM);
  if (!team) fail(`Could not find team folder: ${DEFAULT_TEAM}`);

  const teamPath = team.path;
  let teamChildren = await pageCollectFiles(page, teamPath);
  let domestic = findByName(teamChildren, DEFAULT_DOMESTIC);
  if (!domestic) {
    const matches = await recursiveFindFolder(page, teamPath, DEFAULT_DOMESTIC, 2);
    if (matches.length !== 1) fail(`Could not uniquely find ${DEFAULT_DOMESTIC}`);
    domestic = matches[0];
  } else {
    domestic.path = `${teamPath}/${domestic.name}`;
  }

  const domesticPath = domestic.path;
  const domesticChildren = await pageCollectFiles(page, domesticPath);
  let finalProductFolder = productFolder;
  if (!finalProductFolder) finalProductFolder = heuristicProductFolder(deviceVer, branch, domesticChildren.filter((item) => item.dir === 1));

  let product = findByName(domesticChildren, finalProductFolder);
  if (!product) {
    const matches = await recursiveFindFolder(page, teamPath, finalProductFolder, 3);
    if (matches.length !== 1) {
      fail(`Could not find remote product folder: ${finalProductFolder}\nThis script does not create team/domestic/product folders automatically; confirm the mapping first.\nAvailable under ${DEFAULT_DOMESTIC}:\n${domesticChildren.map((item) => `  ${item.name}`).join("\n")}`);
    }
    product = matches[0];
  } else {
    product.path = `${domesticPath}/${product.name}`;
  }

  const productPath = product.path;
  const releaseName = releaseTime;
  let productChildren = await pageCollectFiles(page, productPath);
  let release = findByName(productChildren, releaseName);
  let releaseCreated = false;
  let releaseWillCreate = false;
  if (!release) {
    const releasePath = `${productPath}/${releaseName}`;
    const canListReleasePath = await pageCanListFolder(page, releasePath);
    if (canListReleasePath) {
      release = { name: releaseName, path: releasePath };
    } else {
      if (!createMissingFolder) {
        fail(`Remote timestamp release folder does not exist: ${releasePath}\nOnly the final YYYYMMDD_HHMM timestamp folder may be created automatically; rerun without --no-create-missing-folder if this is the intended release folder.`);
      }
      if (dryRun) {
        releaseWillCreate = true;
        release = { name: releaseName, path: releasePath };
      } else {
        const mkdirResult = await pageMkdir(page, releasePath);
        if (mkdirResult.result !== "succ") {
          fail(`Could not create remote timestamp release folder ${releasePath}: ${mkdirResult.errmsg || JSON.stringify(mkdirResult)}`);
        }
        releaseCreated = true;
        productChildren = await pageCollectFiles(page, productPath);
        release = findByName(productChildren, releaseName);
        if (!release) {
          const createdCanList = await pageCanListFolder(page, releasePath);
          if (createdCanList) {
            release = { name: releaseName, path: releasePath };
          } else {
            fail(`Created timestamp release folder but could not re-list it: ${releasePath}`);
          }
        }
      }
    }
  }
  release.path = `${productPath}/${release.name}`;

  return {
    teamPath,
    domesticPath,
    productPath,
    productFolder: product.name,
    releasePath: release.path,
    releaseFolder: release.name,
    releaseCreated,
    releaseWillCreate,
  };
}

async function uploadFile(page, localFile, remoteDir, replaceExisting) {
  const inputId = `codex_upload_${Date.now()}_${Math.floor(Math.random() * 100000)}`;
  await page.evaluate((id) => {
    const old = document.getElementById(id);
    if (old) old.remove();
    const input = document.createElement("input");
    input.type = "file";
    input.id = id;
    input.style.display = "none";
    document.body.appendChild(input);
  }, inputId);
  await page.setInputFiles(`#${inputId}`, localFile.path);
  return page.evaluate(async ({ inputId, remoteDir, remoteName, replaceExisting, OVERWRITE_KEEP_NAME }) => {
    const mod = await import("/assets/index-CMZOY5-G.js");
    const api = mod.d;
    const input = document.getElementById(inputId);
    const file = input && input.files && input.files[0];
    if (!file) throw new Error(`Could not read selected local file: ${remoteName}`);

    const uploadPath = `${remoteDir}/${remoteName}`;
    let checked = false;
    try {
      const check = await api.file.checkUpload({
        size: file.size,
        path: uploadPath,
        overwrite: OVERWRITE_KEEP_NAME,
      });
      checked = true;
      if (check.result !== "succ") {
        throw new Error(check.errmsg || `checkUpload failed for ${remoteName}`);
      }
      if (check.uploadName && check.uploadName !== remoteName) {
        throw new Error(`Remote changed upload name from ${remoteName} to ${check.uploadName}`);
      }

      const from = check.from || 0;
      const encodedPath = encodeURI(uploadPath);
      const form = new FormData();
      form.append("trim-upload-file", from ? file.slice(from) : file, file.name);
      const response = await fetch("/upload", {
        method: "POST",
        headers: {
          "Trim-Path": encodedPath,
          "Trim-From": String(from),
          "Trim-Overwrite": String(OVERWRITE_KEEP_NAME),
          "Trim-Mtim": String(Math.floor(file.lastModified / 1000)),
          "Trim-Token": mod.aY(),
          "Trim-Sign": mod.kA(encodedPath),
        },
        body: form,
      });
      const text = await response.text().catch(() => "");
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
      }
      return { name: remoteName, size: file.size, status: response.status, response: text.slice(0, 500) };
    } catch (error) {
      if (checked && !replaceExisting) {
        await api.file.rm({
          files: [uploadPath, uploadPath.replace(/~#(\d+)$/, "~@$1")],
          moveToTrashbin: false,
        }).catch(() => null);
      }
      throw error;
    } finally {
      if (input) input.remove();
    }
  }, {
    inputId,
    remoteDir,
    remoteName: localFile.name,
    replaceExisting,
    OVERWRITE_KEEP_NAME,
  });
}

async function main() {
  const args = parseArgs(process.argv);
  const repo = path.resolve(args.repo);
  const skillDir = path.resolve(__dirname, "..");
  const { deviceVer: currentDeviceVer, releaseTime: inferredReleaseTime } = extractDeviceVer(repo);
  const releaseTime = args.releaseTime || inferredReleaseTime;
  if (!/^\d{8}_\d{4}$/.test(releaseTime)) fail(`Invalid release time: ${releaseTime}`);
  const deviceVer = deviceVerForReleaseTime(currentDeviceVer, releaseTime);

  const branch = runGit(repo, ["branch", "--show-current"]) || "(unknown)";
  const commit = runGit(repo, ["rev-parse", "--short", "HEAD"]) || "(unknown)";
  const mapping = chooseMappedProductFolder({
    repo,
    branch,
    deviceVer,
    explicitFolder: args.remoteProductFolder,
    skillDir,
  });
  const localFiles = args.preflight ? expectedRemoteFiles(args, deviceVer) : chooseLocalFiles(args, repo, deviceVer, releaseTime);

  console.log(`repo: ${repo}`);
  console.log(`branch: ${branch}`);
  console.log(`commit: ${commit}`);
  console.log(`yl_device_ver: ${deviceVer}`);
  console.log(`release_time: ${releaseTime}`);
  console.log(`remote_product_folder: ${mapping.folder || "(heuristic)"} (${mapping.source})`);
  console.log(args.preflight ? "expected_remote_files:" : "local_files:");
  for (const file of localFiles) {
    const sizeText = typeof file.size === "number" ? ` (${file.size} bytes)` : "";
    console.log(`  ${file.name}${sizeText}`);
  }

  const credentials = loadCredentials();
  const { chromium } = requirePlaywright();
  const executablePath = existingBrowserPath();
  const launchOptions = {
    headless: !args.headed,
  };
  if (executablePath) launchOptions.executablePath = executablePath;

  const browser = await chromium.launch(launchOptions);
  const page = await browser.newPage({ ignoreHTTPSErrors: true });
  page.setDefaultTimeout(600000);
  try {
    await login(page, credentials);
    const remote = await resolveRemoteTarget(page, {
      productFolder: mapping.folder,
      releaseTime,
      deviceVer,
      branch,
      createMissingFolder: args.createMissingFolder,
      dryRun: args.dryRun,
    });

    console.log(`remote_release_path: ${remote.releasePath}`);
    if (remote.releaseCreated) console.log("remote_release_folder_created: true");
    if (args.dryRun && remote.releaseWillCreate) {
      console.log("dry_run: timestamp release folder is missing and would be created during a real upload.");
      return;
    }
    const before = await pageCollectFiles(page, remote.releasePath);
    const existing = new Map(before.map((item) => [item.name, item]));
    const collisions = localFiles.filter((file) => existing.has(file.name));
    if (collisions.length && !args.replaceExisting) {
      if (!args.allowExistingIdentical || args.preflight) {
        fail(`Remote same-name files already exist. Refusing to overwrite:\n${collisions.map((file) => `  ${file.name}`).join("\n")}`);
      }
      const unknown = [];
      const mismatched = [];
      const identical = [];
      for (const file of collisions) {
        const remoteFile = existing.get(file.name);
        if (typeof remoteFile.size !== "number" || typeof file.size !== "number") {
          unknown.push(file.name);
        } else if (remoteFile.size !== file.size) {
          mismatched.push(`${file.name}: local=${file.size}, remote=${remoteFile.size}`);
        } else {
          identical.push(file.name);
        }
      }
      if (unknown.length || mismatched.length) {
        fail(`Remote same-name files already exist but are not confirmed identical.\nUnknown size:\n${unknown.map((name) => `  ${name}`).join("\n") || "  (none)"}\nSize mismatch:\n${mismatched.map((name) => `  ${name}`).join("\n") || "  (none)"}`);
      }
      console.log(`remote_existing_identical: ${identical.length} file(s) will be skipped.`);
    }

    if (args.dryRun) {
      console.log("dry_run: remote path resolved, no upload performed.");
      return;
    }

    const uploadFiles = args.allowExistingIdentical && !args.replaceExisting
      ? localFiles.filter((file) => {
          const remoteFile = existing.get(file.name);
          return !remoteFile || remoteFile.size !== file.size;
        })
      : localFiles;
    for (const file of uploadFiles) {
      console.log(`uploading: ${file.name}`);
      const result = await uploadFile(page, file, remote.releasePath, args.replaceExisting);
      console.log(`uploaded: ${result.name} (${result.size} bytes)`);
    }

    const after = await pageCollectFiles(page, remote.releasePath);
    const afterMap = new Map(after.map((item) => [item.name, item]));
    const missing = [];
    const sizeMismatch = [];
    for (const file of localFiles) {
      const remoteFile = afterMap.get(file.name);
      if (!remoteFile) {
        missing.push(file.name);
      } else if (typeof remoteFile.size === "number" && remoteFile.size !== file.size) {
        sizeMismatch.push(`${file.name}: local=${file.size}, remote=${remoteFile.size}`);
      }
    }
    if (missing.length || sizeMismatch.length) {
      fail(`Upload verification failed.\nMissing:\n${missing.map((name) => `  ${name}`).join("\n") || "  (none)"}\nSize mismatch:\n${sizeMismatch.map((name) => `  ${name}`).join("\n") || "  (none)"}`);
    }
    console.log("verify: upload files are present with matching sizes.");
  } finally {
    await browser.close().catch(() => null);
  }
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
});
