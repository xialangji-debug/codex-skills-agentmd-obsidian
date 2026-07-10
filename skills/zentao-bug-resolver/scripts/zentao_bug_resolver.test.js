"use strict";

const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");

const resolver = require("./zentao_bug_resolver");

assert.doesNotThrow(() => require("playwright"));

const defaults = resolver.parseArgs(["node", "resolver"]);
assert.strictEqual(defaults.assignTo, "");
assert.strictEqual(defaults.minimal, false);

const minimal = resolver.parseArgs([
  "node", "resolver", "--ids", "2866", "--assign-to", "self", "--comment", "ignored", "--minimal",
]);
assert.strictEqual(minimal.resolution, "fixed");
assert.strictEqual(minimal.assignTo, "");
assert.strictEqual(minimal.comment, "");
assert.strictEqual(minimal.minimal, true);
assert.throws(
  () => resolver.parseArgs(["node", "resolver", "--plan", "plan.md", "--minimal"]),
  /--minimal only supports --ids/,
);

const builds = [
  { value: "trunk", text: "主干" },
  { value: "release", text: "发布版本" },
];
assert.deepStrictEqual(resolver.pickBuildOption(builds, "release"), { value: "release", label: "发布版本" });
assert.deepStrictEqual(resolver.pickBuildOption(builds, "missing-branch"), {
  value: "trunk",
  label: "主干",
  fallbackFrom: "missing-branch",
});

const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "zentao-resolver-test-"));
try {
  const markdownPath = path.join(tempDir, "plan.md");
  fs.writeFileSync(markdownPath, `# Zentao Resolve Plan

## Bug #2936 单行备注
resolution: fixed
resolvedBuild: trunk
comment: 当前分支已修复，提交 bad3bc47d。

## Bug #2959 多行备注
resolution: external
resolvedBuild:
comment:
平台字段解析异常。
设备端上报正常。
`, "utf8");

  const items = resolver.parseMarkdownPlan(markdownPath);
  assert.strictEqual(items.length, 2);
  assert.strictEqual(items[0].comment, "当前分支已修复，提交 bad3bc47d。");
  assert.strictEqual(items[1].comment, "平台字段解析异常。\n设备端上报正常。");

  const jsonPath = path.join(tempDir, "plan.json");
  fs.writeFileSync(jsonPath, JSON.stringify({ bugs: [{ id: 2936, comment: "JSON 备注" }] }), "utf8");
  assert.strictEqual(resolver.parseJsonPlan(jsonPath)[0].comment, "JSON 备注");
} finally {
  fs.rmSync(tempDir, { recursive: true, force: true });
}

console.log("zentao_bug_resolver tests passed");
