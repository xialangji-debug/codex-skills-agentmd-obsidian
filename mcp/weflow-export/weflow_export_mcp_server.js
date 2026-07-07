const fs = require("fs");
const fsp = require("fs/promises");
const path = require("path");
const os = require("os");
const http = require("http");
const crypto = require("crypto");
const childProcess = require("child_process");

const SERVER_NAME = "weflow-export-mcp";
const SERVER_VERSION = "0.1.0";
const DEFAULT_PORT = 5031;
const DEFAULT_HOST = "127.0.0.1";
const USER_DATA_DIR =
  process.env.WEFLOW_USER_DATA ||
  (process.env.APPDATA
    ? path.join(process.env.APPDATA, "weflow")
    : path.join(os.homedir(), "AppData", "Roaming", "weflow"));
const CONFIG_PATH = path.join(USER_DATA_DIR, "WeFlow-config.json");
const LOG_PATH = path.join(USER_DATA_DIR, "logs", "wcdb.log");
const DEFAULT_EXPORT_DIR = path.join(os.homedir(), "Documents", "WeFlow MCP Exports");

const tools = [
  {
    name: "weflow_status",
    description:
      "Diagnose local WeFlow setup, HTTP API status, config readiness, running processes, and recent WCDB log lines. Secrets are redacted.",
    inputSchema: {
      type: "object",
      properties: {
        tailLines: {
          type: "integer",
          minimum: 0,
          maximum: 300,
          default: 80,
          description: "How many recent wcdb.log lines to include."
        }
      }
    }
  },
  {
    name: "weflow_enable_http_api",
    description:
      "Enable WeFlow's official local HTTP API in WeFlow-config.json and create an access token if needed. A running WeFlow app usually needs restart to pick this up.",
    inputSchema: {
      type: "object",
      properties: {
        port: {
          type: "integer",
          minimum: 1,
          maximum: 65535,
          default: DEFAULT_PORT
        },
        host: {
          type: "string",
          default: DEFAULT_HOST,
          description: "Bind host. Use 127.0.0.1 unless you intentionally expose it to LAN."
        },
        rotateToken: {
          type: "boolean",
          default: false,
          description: "Generate a new HTTP API token even if one already exists."
        }
      }
    }
  },
  {
    name: "weflow_http_health",
    description:
      "Check whether WeFlow's local HTTP API is reachable. This only calls /health and does not need the access token.",
    inputSchema: {
      type: "object",
      properties: {
        port: { type: "integer", minimum: 1, maximum: 65535 },
        host: { type: "string" }
      }
    }
  },
  {
    name: "weflow_list_sessions",
    description:
      "List WeFlow chat sessions through the local HTTP API. Requires WeFlow HTTP API and a completed WeFlow database setup.",
    inputSchema: {
      type: "object",
      properties: {
        keyword: {
          type: "string",
          description: "Optional chat name or wxid filter."
        },
        limit: {
          type: "integer",
          minimum: 1,
          maximum: 10000,
          default: 100
        },
        format: {
          type: "string",
          enum: ["json", "chatlab"],
          default: "json"
        }
      }
    }
  },
  {
    name: "weflow_get_messages",
    description:
      "Fetch messages from one WeFlow session through the local HTTP API. Use talker wxid/chatroom id from weflow_list_sessions.",
    inputSchema: {
      type: "object",
      required: ["talker"],
      properties: {
        talker: {
          type: "string",
          description: "Session username, for example a wxid or *chatroom id."
        },
        keyword: {
          type: "string",
          description: "Optional message keyword search inside this session."
        },
        limit: {
          type: "integer",
          minimum: 1,
          maximum: 10000,
          default: 100
        },
        offset: {
          type: "integer",
          minimum: 0,
          default: 0
        },
        start: {
          type: "string",
          description: "Optional start time accepted by WeFlow, such as a timestamp or date."
        },
        end: {
          type: "string",
          description: "Optional end time accepted by WeFlow, such as a timestamp or date."
        },
        format: {
          type: "string",
          enum: ["json", "chatlab"],
          default: "json"
        },
        media: {
          type: "boolean",
          default: false,
          description: "Ask WeFlow to resolve/export media for returned messages."
        }
      }
    }
  },
  {
    name: "weflow_export_chat",
    description:
      "Export one chat to JSONL, Markdown, and/or CSV by paging WeFlow's local HTTP API. Provide talker, or a sessionKeyword that matches exactly one session.",
    inputSchema: {
      type: "object",
      properties: {
        talker: {
          type: "string",
          description: "Session username from weflow_list_sessions."
        },
        sessionKeyword: {
          type: "string",
          description: "Optional chat name or wxid search. Used only when talker is omitted."
        },
        outputDir: {
          type: "string",
          description: "Directory for exported files. Defaults to Documents/WeFlow MCP Exports."
        },
        formats: {
          type: "array",
          items: { type: "string", enum: ["jsonl", "markdown", "csv"] },
          default: ["jsonl", "markdown"]
        },
        pageSize: {
          type: "integer",
          minimum: 1,
          maximum: 5000,
          default: 1000
        },
        maxMessages: {
          type: "integer",
          minimum: 1,
          maximum: 1000000,
          description: "Optional safety cap."
        },
        start: {
          type: "string",
          description: "Optional start time accepted by WeFlow."
        },
        end: {
          type: "string",
          description: "Optional end time accepted by WeFlow."
        },
        includeMedia: {
          type: "boolean",
          default: false
        }
      }
    }
  },
  {
    name: "weflow_list_exports",
    description:
      "List recent files exported by this MCP or an explicitly provided export directory.",
    inputSchema: {
      type: "object",
      properties: {
        dir: {
          type: "string",
          description: "Directory to scan. Defaults to Documents/WeFlow MCP Exports."
        },
        limit: {
          type: "integer",
          minimum: 1,
          maximum: 1000,
          default: 50
        }
      }
    }
  }
];

function readJsonFile(filePath, fallback = {}) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return fallback;
  }
}

async function writeJsonFile(filePath, value) {
  await fsp.mkdir(path.dirname(filePath), { recursive: true });
  await fsp.writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function redactConfig(config) {
  if (Array.isArray(config)) return config.map((item) => redactConfig(item));
  if (!config || typeof config !== "object") return config;
  const copy = {};
  for (const [key, value] of Object.entries(config)) {
    if (/key|password|token|secret|auth|cookie/i.test(key)) {
      copy[key] = value ? "<redacted>" : value;
    } else if (value && typeof value === "object") {
      copy[key] = redactConfig(value);
    } else {
      copy[key] = value;
    }
  }
  return copy;
}

function expandPath(value) {
  let s = String(value || "").trim();
  if (!s) return "";
  if (s === "~") return os.homedir();
  if (s.startsWith("~/") || s.startsWith("~\\")) return path.join(os.homedir(), s.slice(2));
  s = s.replace(/%([^%]+)%/g, (_, name) => process.env[name] || `%${name}%`);
  return path.resolve(s);
}

function clampInt(value, fallback, min, max) {
  const n = Number.parseInt(String(value ?? ""), 10);
  if (!Number.isFinite(n)) return fallback;
  return Math.min(Math.max(n, min), max);
}

function getApiSettings() {
  const config = readJsonFile(CONFIG_PATH, {});
  const host = String(config.httpApiHost || DEFAULT_HOST).trim() || DEFAULT_HOST;
  const port = clampInt(config.httpApiPort, DEFAULT_PORT, 1, 65535);
  const token = String(config.httpApiToken || "").trim();
  return { config, host, port, token };
}

function httpJsonRequest(method, routePath, query = {}, body = undefined, options = {}) {
  return new Promise((resolve) => {
    const settings = getApiSettings();
    const host = options.host || settings.host || DEFAULT_HOST;
    const port = clampInt(options.port, settings.port || DEFAULT_PORT, 1, 65535);
    const token = options.token !== undefined ? options.token : settings.token;
    const urlPath = new URL(routePath, `http://${host}:${port}`);
    for (const [key, value] of Object.entries(query || {})) {
      if (value === undefined || value === null || value === "") continue;
      urlPath.searchParams.set(key, String(value));
    }
    const payload = body === undefined ? undefined : JSON.stringify(body);
    const headers = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    if (payload !== undefined) {
      headers["Content-Type"] = "application/json";
      headers["Content-Length"] = Buffer.byteLength(payload);
    }
    const req = http.request(
      {
        host,
        port,
        method,
        path: `${urlPath.pathname}${urlPath.search}`,
        headers,
        timeout: options.timeoutMs || 30000
      },
      (res) => {
        const chunks = [];
        res.on("data", (chunk) => chunks.push(chunk));
        res.on("end", () => {
          const text = Buffer.concat(chunks).toString("utf8");
          let data = text;
          try {
            data = text ? JSON.parse(text) : null;
          } catch {
            data = text;
          }
          resolve({
            ok: res.statusCode >= 200 && res.statusCode < 300,
            statusCode: res.statusCode,
            data,
            host,
            port,
            path: `${urlPath.pathname}${urlPath.search}`
          });
        });
      }
    );
    req.on("timeout", () => {
      req.destroy(new Error("Request timed out"));
    });
    req.on("error", (error) => {
      resolve({
        ok: false,
        statusCode: 0,
        error: error.message,
        host,
        port,
        path: `${urlPath.pathname}${urlPath.search}`
      });
    });
    if (payload !== undefined) req.write(payload);
    req.end();
  });
}

function tasklistWeFlow() {
  if (process.platform !== "win32") return { supported: false, processes: [] };
  try {
    const output = childProcess.execFileSync("tasklist", ["/FI", "IMAGENAME eq WeFlow.exe", "/FO", "CSV", "/NH"], {
      encoding: "utf8",
      windowsHide: true,
      timeout: 5000
    });
    const processes = output
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line && !/^INFO:/i.test(line))
      .map((line) => {
        const cols = parseCsvLine(line);
        return { imageName: cols[0], pid: Number(cols[1]) || cols[1], sessionName: cols[2], memUsage: cols[4] };
      })
      .filter((p) => /weflow\.exe/i.test(String(p.imageName || "")));
    return { supported: true, processes };
  } catch (error) {
    return { supported: true, error: error.message, processes: [] };
  }
}

function parseCsvLine(line) {
  const out = [];
  let cur = "";
  let quoted = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (quoted) {
      if (ch === '"' && line[i + 1] === '"') {
        cur += '"';
        i++;
      } else if (ch === '"') {
        quoted = false;
      } else {
        cur += ch;
      }
    } else if (ch === '"') {
      quoted = true;
    } else if (ch === ",") {
      out.push(cur);
      cur = "";
    } else {
      cur += ch;
    }
  }
  out.push(cur);
  return out;
}

function tailText(filePath, lines) {
  if (!lines) return [];
  try {
    const text = fs.readFileSync(filePath, "utf8");
    return text.split(/\r?\n/).filter(Boolean).slice(-lines);
  } catch {
    return [];
  }
}

function pathInfo(filePath) {
  try {
    const st = fs.statSync(filePath);
    return {
      exists: true,
      isDirectory: st.isDirectory(),
      isFile: st.isFile(),
      size: st.size,
      mtime: st.mtime.toISOString()
    };
  } catch {
    return { exists: false };
  }
}

function discoverWechatRoots(config) {
  const candidates = [
    config.dbPath,
    "C:\\WeChatData\\xwechat_files",
    "C:\\缓存\\xwechat_files",
    path.join(os.homedir(), "Documents", "WeChat Files"),
    path.join(os.homedir(), "Documents", "xwechat_files")
  ]
    .filter(Boolean)
    .map(expandPath);
  const unique = Array.from(new Set(candidates));
  return unique.map((candidate) => {
    const info = pathInfo(candidate);
    let children = [];
    if (info.exists && info.isDirectory) {
      try {
        children = fs
          .readdirSync(candidate, { withFileTypes: true })
          .filter((entry) => entry.isDirectory())
          .slice(0, 20)
          .map((entry) => entry.name);
      } catch {
        children = [];
      }
    }
    return { path: candidate, ...info, children };
  });
}

async function statusTool(args) {
  const tailLines = clampInt(args.tailLines, 80, 0, 300);
  const config = readJsonFile(CONFIG_PATH, {});
  const processInfo = tasklistWeFlow();
  const health = await httpJsonRequest("GET", "/health", {}, undefined, {
    token: "",
    timeoutMs: 2500
  });
  const logTail = tailText(LOG_PATH, tailLines);
  const logText = logTail.join("\n");
  const setup = {
    configPath: CONFIG_PATH,
    configFile: pathInfo(CONFIG_PATH),
    logPath: LOG_PATH,
    logFile: pathInfo(LOG_PATH),
    userDataDir: USER_DATA_DIR,
    wechatRoots: discoverWechatRoots(config)
  };
  const readiness = {
    onboardingDone: config.onboardingDone === true,
    dbPathConfigured: !!String(config.dbPath || "").trim(),
    decryptKeyPresent: !!String(config.decryptKey || "").trim(),
    myWxidConfigured: !!String(config.myWxid || "").trim(),
    httpApiEnabled: config.httpApiEnabled === true,
    httpApiTokenPresent: !!String(config.httpApiToken || "").trim(),
    httpApiHost: config.httpApiHost || DEFAULT_HOST,
    httpApiPort: config.httpApiPort || DEFAULT_PORT,
    httpApiReachable: health.ok === true
  };
  const findings = [];
  if (!readiness.dbPathConfigured) findings.push("WeFlow dbPath is empty.");
  if (!readiness.decryptKeyPresent) findings.push("WeFlow decryptKey is empty.");
  if (!readiness.myWxidConfigured) findings.push("WeFlow myWxid is empty.");
  if (!readiness.onboardingDone) findings.push("WeFlow onboardingDone is false.");
  if (!readiness.httpApiEnabled) findings.push("WeFlow HTTP API is disabled in config.");
  if (!readiness.httpApiTokenPresent) findings.push("WeFlow HTTP API token is missing.");
  if (!health.ok) findings.push(`WeFlow HTTP API is not reachable on ${health.host}:${health.port}.`);
  if (/InitProtection call/.test(logText) && !/open account success|HTTP API server started/i.test(logText)) {
    findings.push("Recent WCDB log shows InitProtection calls without a visible successful DB open.");
  }
  if (/-1006/.test(logText)) findings.push("Recent WCDB log mentions error code -1006.");
  return {
    success: true,
    readiness,
    findings,
    processInfo,
    httpHealth: health,
    setup,
    config: redactConfig(config),
    logTail
  };
}

async function enableHttpApiTool(args) {
  const config = readJsonFile(CONFIG_PATH, {});
  const port = clampInt(args.port, config.httpApiPort || DEFAULT_PORT, 1, 65535);
  const host = String(args.host || config.httpApiHost || DEFAULT_HOST).trim() || DEFAULT_HOST;
  const hadToken = !!String(config.httpApiToken || "").trim();
  if (args.rotateToken || !hadToken) {
    config.httpApiToken = crypto.randomBytes(32).toString("base64url");
  }
  config.httpApiEnabled = true;
  config.httpApiPort = port;
  config.httpApiHost = host;
  await writeJsonFile(CONFIG_PATH, config);
  const processInfo = tasklistWeFlow();
  const health = await httpJsonRequest("GET", "/health", {}, undefined, {
    token: "",
    host,
    port,
    timeoutMs: 2500
  });
  return {
    success: true,
    configPath: CONFIG_PATH,
    httpApiEnabled: true,
    httpApiHost: host,
    httpApiPort: port,
    tokenPresent: !!config.httpApiToken,
    tokenCreated: args.rotateToken || !hadToken,
    apiReachableNow: health.ok,
    health,
    restartLikelyNeeded: processInfo.processes.length > 0 && !health.ok,
    note:
      processInfo.processes.length > 0 && !health.ok
        ? "WeFlow is already running, so restart WeFlow to let it auto-start the HTTP API."
        : "If WeFlow is not running, start it after configuration."
  };
}

async function healthTool(args) {
  const settings = getApiSettings();
  const host = args.host || settings.host || DEFAULT_HOST;
  const port = clampInt(args.port, settings.port || DEFAULT_PORT, 1, 65535);
  const health = await httpJsonRequest("GET", "/health", {}, undefined, {
    token: "",
    host,
    port,
    timeoutMs: 3000
  });
  return {
    success: health.ok,
    configured: {
      enabled: settings.config.httpApiEnabled === true,
      host: settings.host,
      port: settings.port,
      tokenPresent: !!settings.token
    },
    health
  };
}

function requireApiToken() {
  const settings = getApiSettings();
  if (!settings.token) {
    const error = new Error("WeFlow HTTP API token is missing. Run weflow_enable_http_api, then restart WeFlow.");
    error.code = "WEFLOW_HTTP_TOKEN_MISSING";
    throw error;
  }
  return settings;
}

async function apiGet(routePath, query = {}) {
  requireApiToken();
  const response = await httpJsonRequest("GET", routePath, query, undefined, { timeoutMs: 60000 });
  if (!response.ok) {
    const error = new Error(
      `WeFlow HTTP API request failed (${response.statusCode || "network"}): ${response.error || JSON.stringify(response.data)}`
    );
    error.response = response;
    throw error;
  }
  return response.data;
}

async function listSessionsRaw(args = {}) {
  const query = {
    keyword: args.keyword || "",
    limit: clampInt(args.limit, 100, 1, 10000),
    format: args.format || ""
  };
  return apiGet("/api/v1/sessions", query);
}

async function listSessionsTool(args) {
  const data = await listSessionsRaw(args);
  return { success: true, data };
}

async function getMessagesTool(args) {
  const talker = String(args.talker || "").trim();
  if (!talker) throw new Error("Missing required argument: talker");
  const query = {
    talker,
    keyword: args.keyword || "",
    limit: clampInt(args.limit, 100, 1, 10000),
    offset: clampInt(args.offset, 0, 0, Number.MAX_SAFE_INTEGER),
    start: args.start || "",
    end: args.end || "",
    format: args.format || "json",
    media: args.media ? "1" : ""
  };
  const data = await apiGet("/api/v1/messages", query);
  return { success: true, data };
}

function normalizeFormats(formats) {
  const allowed = new Set(["jsonl", "markdown", "csv"]);
  const requested = Array.isArray(formats) && formats.length > 0 ? formats : ["jsonl", "markdown"];
  const normalized = Array.from(new Set(requested.map((f) => String(f).toLowerCase()).filter((f) => allowed.has(f))));
  return normalized.length ? normalized : ["jsonl", "markdown"];
}

function getMessagesFromApiResponse(data) {
  if (Array.isArray(data?.messages)) return data.messages;
  if (Array.isArray(data?.data?.messages)) return data.data.messages;
  if (Array.isArray(data?.chat?.messages)) return data.chat.messages;
  return [];
}

function getHasMoreFromApiResponse(data) {
  if (typeof data?.hasMore === "boolean") return data.hasMore;
  if (typeof data?.sync?.hasMore === "boolean") return data.sync.hasMore;
  return false;
}

function displayTime(message) {
  const raw =
    message.createTime ??
    message.create_time ??
    message.timestamp ??
    message.time ??
    message.createdAt ??
    message.msgTime ??
    0;
  const n = Number(raw);
  if (!Number.isFinite(n) || n <= 0) return "";
  const millis = n > 100000000000 ? n : n * 1000;
  try {
    return new Date(millis).toISOString().replace("T", " ").replace(/\.\d{3}Z$/, "Z");
  } catch {
    return String(raw);
  }
}

function messageContent(message) {
  const value =
    message.content ??
    message.parsedContent ??
    message.text ??
    message.rawContent ??
    message.raw_content ??
    message.message ??
    "";
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

function messageSender(message) {
  return (
    message.senderDisplayName ||
    message.senderName ||
    message.senderUsername ||
    message.from ||
    (message.isSend === 1 || message.isSend === true ? "me" : "other")
  );
}

function messageType(message) {
  return String(message.typeLabel || message.messageType || message.localType || message.type || "");
}

function safeFilePart(value) {
  const s = String(value || "chat")
    .replace(/[<>:"/\\|?*\x00-\x1F]/g, "_")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 80);
  return s || "chat";
}

function csvEscape(value) {
  const s = String(value ?? "");
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

async function resolveTalker(args) {
  const talker = String(args.talker || "").trim();
  if (talker) return { talker, session: null };
  const keyword = String(args.sessionKeyword || "").trim();
  if (!keyword) throw new Error("Provide talker or sessionKeyword.");
  const sessionsResponse = await listSessionsRaw({ keyword, limit: 20, format: "json" });
  const sessions = Array.isArray(sessionsResponse?.sessions)
    ? sessionsResponse.sessions
    : Array.isArray(sessionsResponse?.data?.sessions)
      ? sessionsResponse.data.sessions
      : [];
  if (sessions.length !== 1) {
    const error = new Error(
      sessions.length === 0
        ? `No WeFlow session matched keyword: ${keyword}`
        : `Multiple WeFlow sessions matched keyword: ${keyword}`
    );
    error.candidates = sessions.map((s) => ({
      username: s.username || s.id,
      displayName: s.displayName || s.name || "",
      type: s.sessionType || s.type || ""
    }));
    throw error;
  }
  return { talker: sessions[0].username || sessions[0].id, session: sessions[0] };
}

async function exportChatTool(args) {
  const formats = normalizeFormats(args.formats);
  const { talker, session } = await resolveTalker(args);
  const pageSize = clampInt(args.pageSize, 1000, 1, 5000);
  const maxMessages = args.maxMessages ? clampInt(args.maxMessages, 1000000, 1, 1000000) : null;
  const outputDir = expandPath(args.outputDir || DEFAULT_EXPORT_DIR);
  await fsp.mkdir(outputDir, { recursive: true });

  const messages = [];
  let offset = 0;
  let hasMore = true;
  while (hasMore) {
    const remaining = maxMessages ? maxMessages - messages.length : pageSize;
    if (remaining <= 0) break;
    const limit = Math.min(pageSize, remaining);
    const data = await apiGet("/api/v1/messages", {
      talker,
      limit,
      offset,
      start: args.start || "",
      end: args.end || "",
      media: args.includeMedia ? "1" : ""
    });
    const batch = getMessagesFromApiResponse(data);
    messages.push(...batch);
    hasMore = getHasMoreFromApiResponse(data) && batch.length > 0;
    offset += batch.length;
    if (batch.length === 0) break;
  }

  const displayName = session?.displayName || session?.name || talker;
  const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
  const baseName = `${stamp}-${safeFilePart(displayName || talker)}`;
  const files = {};

  if (formats.includes("jsonl")) {
    const filePath = path.join(outputDir, `${baseName}.jsonl`);
    const body = messages.map((message) => JSON.stringify(message)).join("\n") + (messages.length ? "\n" : "");
    await fsp.writeFile(filePath, body, "utf8");
    files.jsonl = filePath;
  }

  if (formats.includes("markdown")) {
    const filePath = path.join(outputDir, `${baseName}.md`);
    const lines = [
      `# ${displayName || talker}`,
      "",
      `- Talker: ${talker}`,
      `- Exported at: ${new Date().toISOString()}`,
      `- Message count: ${messages.length}`,
      "",
      "---",
      ""
    ];
    for (let i = 0; i < messages.length; i++) {
      const message = messages[i];
      lines.push(`## ${i + 1}. ${displayTime(message) || "Unknown time"}`);
      lines.push("");
      lines.push(`- Sender: ${messageSender(message)}`);
      lines.push(`- Type: ${messageType(message) || "unknown"}`);
      lines.push("");
      lines.push(messageContent(message) || "");
      lines.push("");
    }
    await fsp.writeFile(filePath, lines.join("\n"), "utf8");
    files.markdown = filePath;
  }

  if (formats.includes("csv")) {
    const filePath = path.join(outputDir, `${baseName}.csv`);
    const header = ["index", "time", "sender", "isSend", "type", "content", "localId", "serverId"];
    const rows = messages.map((message, index) => [
      index + 1,
      displayTime(message),
      messageSender(message),
      message.isSend ?? "",
      messageType(message),
      messageContent(message),
      message.localId ?? message.local_id ?? "",
      message.serverId ?? message.server_id ?? ""
    ]);
    const csv = [header, ...rows].map((row) => row.map(csvEscape).join(",")).join("\r\n") + "\r\n";
    await fsp.writeFile(filePath, `\uFEFF${csv}`, "utf8");
    files.csv = filePath;
  }

  return {
    success: true,
    talker,
    displayName,
    messageCount: messages.length,
    outputDir,
    files,
    capped: !!maxMessages && messages.length >= maxMessages
  };
}

async function listExportsTool(args) {
  const dir = expandPath(args.dir || DEFAULT_EXPORT_DIR);
  const limit = clampInt(args.limit, 50, 1, 1000);
  let entries = [];
  try {
    entries = await fsp.readdir(dir, { withFileTypes: true });
  } catch (error) {
    return { success: false, dir, error: error.message, files: [] };
  }
  const allowed = new Set([".jsonl", ".json", ".md", ".csv", ".html", ".txt", ".xlsx"]);
  const files = [];
  for (const entry of entries) {
    if (!entry.isFile()) continue;
    const filePath = path.join(dir, entry.name);
    if (!allowed.has(path.extname(entry.name).toLowerCase())) continue;
    try {
      const st = await fsp.stat(filePath);
      files.push({
        path: filePath,
        name: entry.name,
        size: st.size,
        mtime: st.mtime.toISOString()
      });
    } catch {
      // Ignore disappeared files.
    }
  }
  files.sort((a, b) => String(b.mtime).localeCompare(String(a.mtime)));
  return { success: true, dir, count: Math.min(files.length, limit), files: files.slice(0, limit) };
}

async function callTool(name, args = {}) {
  switch (name) {
    case "weflow_status":
      return statusTool(args);
    case "weflow_enable_http_api":
      return enableHttpApiTool(args);
    case "weflow_http_health":
      return healthTool(args);
    case "weflow_list_sessions":
      return listSessionsTool(args);
    case "weflow_get_messages":
      return getMessagesTool(args);
    case "weflow_export_chat":
      return exportChatTool(args);
    case "weflow_list_exports":
      return listExportsTool(args);
    default:
      throw new Error(`Unknown tool: ${name}`);
  }
}

function jsonText(value) {
  return JSON.stringify(value, null, 2);
}

function sendMessage(message) {
  const body = JSON.stringify(message);
  process.stdout.write(`Content-Length: ${Buffer.byteLength(body, "utf8")}\r\n\r\n${body}`);
}

function sendResult(id, result) {
  sendMessage({ jsonrpc: "2.0", id, result });
}

function sendError(id, code, message, data) {
  sendMessage({ jsonrpc: "2.0", id, error: { code, message, data } });
}

async function handleMessage(message) {
  const id = message.id;
  try {
    if (message.method === "initialize") {
      sendResult(id, {
        protocolVersion: message.params?.protocolVersion || "2024-11-05",
        capabilities: { tools: {} },
        serverInfo: { name: SERVER_NAME, version: SERVER_VERSION }
      });
      return;
    }
    if (message.method === "notifications/initialized" || message.method?.startsWith("notifications/")) {
      return;
    }
    if (message.method === "tools/list") {
      sendResult(id, { tools });
      return;
    }
    if (message.method === "tools/call") {
      const toolName = message.params?.name;
      const args = message.params?.arguments || {};
      try {
        const result = await callTool(toolName, args);
        sendResult(id, { content: [{ type: "text", text: jsonText(result) }] });
      } catch (error) {
        const payload = {
          success: false,
          error: error.message,
          code: error.code,
          candidates: error.candidates,
          response: error.response
        };
        sendResult(id, {
          isError: true,
          content: [{ type: "text", text: jsonText(payload) }]
        });
      }
      return;
    }
    if (id !== undefined) sendError(id, -32601, `Method not found: ${message.method}`);
  } catch (error) {
    if (id !== undefined) sendError(id, -32603, error.message);
  }
}

let inputBuffer = Buffer.alloc(0);

function tryReadMessages() {
  for (;;) {
    const headerEnd = inputBuffer.indexOf("\r\n\r\n");
    if (headerEnd === -1) {
      const newline = inputBuffer.indexOf("\n");
      if (newline === -1) return;
      const line = inputBuffer.slice(0, newline).toString("utf8").trim();
      if (!line) {
        inputBuffer = inputBuffer.slice(newline + 1);
        continue;
      }
      if (!line.startsWith("{")) return;
      inputBuffer = inputBuffer.slice(newline + 1);
      try {
        handleMessage(JSON.parse(line));
      } catch {
        // Ignore malformed newline-framed input.
      }
      continue;
    }
    const header = inputBuffer.slice(0, headerEnd).toString("utf8");
    const match = /content-length:\s*(\d+)/i.exec(header);
    if (!match) {
      inputBuffer = inputBuffer.slice(headerEnd + 4);
      continue;
    }
    const length = Number.parseInt(match[1], 10);
    const bodyStart = headerEnd + 4;
    const bodyEnd = bodyStart + length;
    if (inputBuffer.length < bodyEnd) return;
    const body = inputBuffer.slice(bodyStart, bodyEnd).toString("utf8");
    inputBuffer = inputBuffer.slice(bodyEnd);
    try {
      handleMessage(JSON.parse(body));
    } catch (error) {
      sendError(null, -32700, error.message);
    }
  }
}

process.stdin.on("data", (chunk) => {
  inputBuffer = Buffer.concat([inputBuffer, chunk]);
  tryReadMessages();
});

process.stdin.resume();
