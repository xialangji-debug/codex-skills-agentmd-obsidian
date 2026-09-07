"use strict";

const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const cp = require("child_process");

const resolver = require("./zentao_bug_resolver");

assert.doesNotThrow(() => require("playwright"));

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
assert.throws(
  () => resolver.parseArgs(["node", "resolver", "--ids", "3310", "--allow-product-mismatch"]),
  /requires --reactivate-resolved/,
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

  const ctx = { repo: tempDir, branch: "sample-main" };
  assert.throws(() => resolver.resolveExpectedProduct(defaults, ctx), /Missing confirmed Zentao product/);
  const blockedOutput = path.join(tempDir, "blocked-output");
  const blocked = cp.spawnSync(process.execPath, [
    path.join(__dirname, "zentao_bug_resolver.js"), "--repo", tempDir,
    "--ids", "1001", "--submit", "--output", blockedOutput,
  ], { encoding: "utf8" });
  assert.strictEqual(blocked.status, 1);
  assert.match(blocked.stderr, /Missing confirmed Zentao product/);
  assert.strictEqual(fs.existsSync(blockedOutput), false);

  const projectDir = path.join(tempDir, ".codex-project");
  fs.mkdirSync(projectDir);
  const legacyPath = path.join(projectDir, "zentao.md");
  fs.writeFileSync(legacyPath, "禅道项目名：`Legacy Product`\n", "utf8");
  assert.strictEqual(resolver.expectedProductFromRepo(tempDir), "Legacy Product");
  fs.writeFileSync(legacyPath, "禅道项目名：`First`\nZentao项目：`Second`\n", "utf8");
  assert.throws(() => resolver.expectedProductFromRepo(tempDir), /Ambiguous legacy/);

  const variantPath = path.join(projectDir, "variant.md");
  const confirmed = "- 映射状态：`confirmed`\n- 禅道产品：`Example MiniApp Asset Edition`\n- branch：`sample-main`\n";
  fs.writeFileSync(variantPath, confirmed, "utf8");
  assert.strictEqual(resolver.expectedProductFromRepo(tempDir), "Example MiniApp Asset Edition");
  assert.strictEqual(resolver.resolveExpectedProduct(defaults, ctx), "Example MiniApp Asset Edition");
  assert.throws(
    () => resolver.resolveExpectedProduct({ ...defaults, expectedProduct: "Example MiniApp" }, ctx),
    /differs from the confirmed/,
  );
  assert.throws(
    () => resolver.resolveExpectedProduct(defaults, { ...ctx, branch: "another-branch" }),
    /different branch/,
  );
  fs.writeFileSync(variantPath, confirmed + "- 禅道产品：`Other Product`\n", "utf8");
  assert.throws(() => resolver.expectedProductFromRepo(tempDir), /Ambiguous variant field/);
  for (const invalid of [
    "- 映射状态：`needs-confirmation`\n- 禅道产品：`Example`\n",
    "- 映射状态：`confirmed`\n- 禅道产品：`未确认`\n",
    "- 映射状态：\n- 禅道产品：`Example`\n",
    "- 映射状态：`confirmed`\n",
  ]) {
    fs.writeFileSync(variantPath, invalid, "utf8");
    assert.throws(() => resolver.expectedProductFromRepo(tempDir), /not confirmed|Missing confirmed/);
  }
  assert.doesNotThrow(() => resolver.resolveExpectedProduct({
    ...defaults, reactivateResolved: true, allowProductMismatch: true,
  }, ctx));
} finally {
  fs.rmSync(tempDir, { recursive: true, force: true });
}

async function verifyMissingProductHasNoPageAccess() {
  let pageAccesses = 0;
  const page = new Proxy({}, { get() { pageAccesses++; throw new Error("Unexpected page access"); } });
  await assert.rejects(
    resolver.processBug(page, { ...defaults, submit: true }, { id: "1001" }),
    /Missing confirmed Zentao product/,
  );
  assert.strictEqual(pageAccesses, 0);
}

function mockBugPage(product, initialStatus = "激活") {
  const trace = { navigations: [], saves: 0 };
  const values = { resolution: "", resolvedBuild: "trunk", assignedTo: "original-user" };
  const locator = {
    first() { return this; },
    async count() { return 1; },
    async click() { trace.saves++; },
  };
  const frame = {
    locator() { return locator; },
    async evaluate(callback, argument) {
      if (typeof argument === "string") {
        return { product, status: trace.saves ? "已解决" : initialStatus, title: "Synthetic bug" };
      }
      if (argument && argument.name) {
        values[argument.name] = argument.value;
        return argument.value;
      }
      if (String(callback).includes("parsePicker")) {
        return {
          title: "Synthetic bug",
          resolutionOptions: [{ value: "fixed", text: "已解决" }],
          buildOptions: [{ value: "trunk", text: "主干" }],
          assignOptions: [{ value: "original-user", text: "Original" }],
          values: { ...values },
        };
      }
      if (String(callback).includes("new FormData")) return Object.entries(values);
      throw new Error("Unexpected mock evaluation");
    },
  };
  return {
    trace,
    async goto(url) { trace.navigations.push(url); },
    async waitForTimeout() {},
    async waitForLoadState() {},
    frames() { return [frame]; },
  };
}

async function verifyRemoteWriteBoundaries() {
  const args = { ...defaults, expectedProduct: "Product A", siteUrl: "https://offline.example.invalid" };
  const item = { id: "1001", title: "Synthetic bug", resolution: "fixed", resolvedBuild: "trunk", assignTo: "", comment: "" };
  const mismatch = mockBugPage("Product B");
  await assert.rejects(resolver.processBug(mismatch, { ...args, submit: true }, item), /product mismatch/);
  assert.strictEqual(mismatch.trace.saves, 0);
  assert.deepStrictEqual(mismatch.trace.navigations, ["https://offline.example.invalid/bug-view-1001.html"]);

  const preview = mockBugPage("Product A");
  const previewResult = await resolver.processBug(preview, args, item);
  assert.strictEqual(previewResult.submitted, false);
  assert.strictEqual(preview.trace.saves, 0);
  assert.strictEqual(previewResult.assignee.value, "original-user");

  const submit = mockBugPage("Product A");
  const submitResult = await resolver.processBug(submit, { ...args, submit: true }, item);
  assert.strictEqual(submitResult.submitted, true);
  assert.strictEqual(submit.trace.saves, 1);
  assert.strictEqual(submitResult.finalStatus, "已解决");

  const correction = mockBugPage("Product B", "已解决");
  const correctionResult = await resolver.processBug(correction, {
    ...args, allowProductMismatch: true, reactivateResolved: true,
  }, item);
  assert.strictEqual(correctionResult.activationPlanned, true);
  assert.strictEqual(correction.trace.saves, 0);
}

verifyMissingProductHasNoPageAccess().then(verifyRemoteWriteBoundaries).then(() => {
  console.log("zentao_bug_resolver tests passed");
}).catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
