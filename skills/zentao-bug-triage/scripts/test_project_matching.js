"use strict";

const assert = require("assert");
const triage = require("./zentao_bug_snapshot");

const parsed = triage.parseProjectMap(`
- branch_contains:
    - example-firmware-main
  zentao_names:
    - Example Firmware Project
  product_names:
    - Example Firmware Product
  project_id: 100
  product_id: 200
`);
assert.deepStrictEqual(parsed[0].zentaoNames, ["Example Firmware Project"]);
assert.deepStrictEqual(parsed[0].productNames, ["Example Firmware Product"]);

const resolved = triage.resolveCurrentProject({
  branch: "example-firmware-main",
  deviceVer: "EXAMPLE_DEVICE_V1",
  deviceName: "EXAMPLE_DEVICE",
  hwVer: "EXAMPLE_HW",
  softVer: "",
  projectMapPath: require("path").join(__dirname, "..", "references", "project-map.md"),
});
assert.strictEqual(resolved.projectName, "Example Firmware Project");
assert.strictEqual(resolved.productName, "Example Firmware Product");
assert.strictEqual(resolved.projectId, "100");
assert.strictEqual(resolved.productId, "200");

const expected = "Example MiniApp Asset Edition";
assert.strictEqual(triage.projectNameMatchesExactly(expected, expected), true);
assert.strictEqual(triage.projectNameMatchesExactly("Example MiniApp", expected), false);
assert.strictEqual(triage.projectNameMatches("Example MiniApp", expected), true);

const rows = [
  { id: "1", product: expected },
  { id: "2", product: "Example MiniApp" },
];
assert.deepStrictEqual(triage.assignedFallbackRows(rows, expected, 80, -1).map((row) => row.id), ["1"]);
assert.deepStrictEqual(
  triage.assignedFallbackRows([{ id: "2", product: "Example MiniApp" }], expected, 80, -1),
  [],
);
assert.deepStrictEqual(
  triage.assignedFallbackRows([{ id: "3", product: "" }], expected, 80, -1).map((row) => row.id),
  ["3"],
);

assert.strictEqual(triage.rowMatchesBugStatus({ status: "active" }, { bugStatus: "active" }), true);
assert.strictEqual(triage.rowMatchesBugStatus({ status: "resolved" }, { bugStatus: "active" }), false);
assert.strictEqual(triage.rowMatchesBugStatus({ status: "active" }, { bugStatus: "unresolved" }), true);
assert.strictEqual(triage.rowMatchesBugStatus({ status: "resolved" }, { bugStatus: "unresolved" }), true);
assert.strictEqual(triage.rowMatchesBugStatus({ status: "closed" }, { bugStatus: "unresolved" }), false);
assert.strictEqual(
  triage.bugFromRow({ id: "4", product: "", title: "test" }, {
    productName: "Example Firmware Product",
    projectName: "Example Firmware Project",
  }).product,
  "Example Firmware Product",
);

const backendIcon = triage.classify({
  title: "连接后台图标为透明状态",
  steps: "正常联网状态，连接后台图标为透明状态，期望绿色高亮",
  product: "Example Firmware Product",
});
assert.strictEqual(backendIcon.category, "UI Bug");
assert.strictEqual(backendIcon.canHandle, "可以先查");

console.log("zentao project matching tests passed");
