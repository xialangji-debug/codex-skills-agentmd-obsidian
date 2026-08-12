"use strict";

const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");

const resolver = require("./zentao_bug_resolver");

assert.strictEqual(typeof resolver.parseArgs, "function");

const defaults = resolver.parseArgs(["node", "resolver"]);
assert.strictEqual(defaults.assignTo, "");
assert.strictEqual(defaults.minimal, false);
assert.strictEqual(defaults.reactivateResolved, false);
assert.strictEqual(defaults.allowProductMismatch, false);

const reactivate = resolver.parseArgs(["node", "resolver", "--ids", "3310", "--reactivate-resolved"]);
assert.strictEqual(reactivate.reactivateResolved, true);
assert.strictEqual(reactivate.activateComment, "误将非当前项目Bug标记为已解决，现恢复激活状态。");
assert.throws(
  () => resolver.parseArgs(["node", "resolver", "--ids", "3310", "--reactivate-resolved", "--activate-closed"]),
  /cannot be combined/,
);

assert.strictEqual(
  resolver.productNamesEqual("Example MiniApp Asset Edition", "Example MiniApp Asset Edition"),
  true,
);
assert.strictEqual(
  resolver.productNamesEqual("Example MiniApp", "Example MiniApp Asset Edition"),
  false,
);

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
