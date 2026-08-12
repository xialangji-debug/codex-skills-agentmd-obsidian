"use strict";

const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { enrichBugsWithMemory } = require("./memory_linkage");

const root = fs.mkdtempSync(path.join(os.tmpdir(), "zentao-memory-linkage-"));

function writeNote(name, content) {
  fs.writeFileSync(path.join(root, name), content, "utf8");
}

writeNote("cloud-album.md", `# 示例固件云相册上传状态修复

## 关键词
云相册、上传失败、album_upload_event

## 适用范围
repo: example_firmware
branch: example_main

## 症状
云相册上传失败后界面没有恢复。

## Key Files
album_upload_event.c

## Verification
验证状态：已验证，真机通过。
`);

writeNote("contact-port.md", `# 联系人数量边界移植

## 关键词
联系人、白名单、数量上限

## 适用范围
另一个客户项目

## 症状
联系人数量超过上限后显示错误。

## Verification
验证状态：已验证。
`);

writeNote("wxpay-context-only.md", `# 示例物卡微信支付扫码镜像切换

## 关键词
示例产品、小程序物卡公版、微信支付、扫码支付、镜像切换

## 适用范围
repo: example_firmware
branch: example_main

## 症状
微信支付扫码预览镜像方向错误。

## Verification
验证状态：已验证。
`);

const managedState = {
  schema_version: 2,
  fix_id: "FP-SYNTHETIC",
  reference_target: "target-synthetic",
  last_reference_target: null,
  targets: [{
    target_id: "target-synthetic",
    verification: "qa_verified",
    implementation: "committed",
    relation: "reference",
  }],
};
writeNote("managed.md", `# Synthetic managed fix

## 关键词
managed_refresh

## 症状
Synthetic managed state is verified.

<!-- codex-fix-state-json: ${Buffer.from(JSON.stringify(managedState), "utf8").toString("base64url")} -->
`);

const ctx = {
  repo: "/workspace/example-firmware",
  repoName: "example_firmware",
  branch: "example_main",
};

function bug(overrides = {}) {
  return {
    id: "1001",
    title: "云相册上传失败后页面不恢复",
    steps: "进入云相册，上传图片并断网",
    expected: "上传失败后应该恢复按钮并提示失败",
    actual: "按钮一直处于上传中",
    product: "Example Device",
    status: "激活",
    category: "UI Bug",
    canHandle: "可以先查",
    handlingBucket: "work",
    detailFetched: true,
    logsNeeded: false,
    attachmentLinks: [],
    attachments: [],
    ...overrides,
  };
}

const high = enrichBugsWithMemory([bug()], ctx, { root }).bugs[0];
assert.strictEqual(high.memoryMatch.level, "高");
assert.strictEqual(high.repairEligibility.label, "可直接修复候选");
assert.strictEqual(high.repairEligibility.directCandidate, true);

const portable = enrichBugsWithMemory([bug({
  id: "1002",
  title: "联系人超过数量上限显示错误",
  steps: "下发多个联系人和白名单",
  expected: "联系人数量达到上限后应该正确提示",
  actual: "联系人列表显示错误",
})], { repo: "/workspace/another", repoName: "another", branch: "customer" }, { root }).bugs[0];
assert.strictEqual(portable.memoryMatch.level, "中");
assert.strictEqual(portable.repairEligibility.label, "可移植候选");
assert.strictEqual(portable.repairEligibility.directCandidate, false);

const miss = enrichBugsWithMemory([bug({
  id: "1003",
  title: "蓝牙扫描列表刷新",
  steps: "进入蓝牙页面刷新",
  expected: "应该显示附近设备",
  actual: "列表为空",
})], ctx, { root }).bugs[0];
assert.strictEqual(miss.memoryMatch.level, "未命中");
assert.strictEqual(miss.repairEligibility.label, "需先查代码");

const productOnly = enrichBugsWithMemory([bug({
  id: "3199",
  title: "测试完成",
  steps: "[步骤][结果][期望]",
  expected: "",
  actual: "",
  product: "示例_小程序物卡公版",
})], ctx, { root }).bugs[0];
assert.strictEqual(productOnly.memoryMatch.level, "未命中");
assert.strictEqual(productOnly.memoryMatch.score, 0);
assert.strictEqual(productOnly.bugFingerprint.hasIssueEvidence, false);
assert.ok(!productOnly.bugFingerprint.terms.includes("程序物"));

const unrelatedSameProduct = enrichBugsWithMemory([bug({
  id: "3181",
  title: "禁用视频通话后小程序一直在拨打状态",
  steps: "关闭视频通话开关后呼叫手表",
  expected: "手表拒接并自动挂断",
  actual: "小程序一直在拨打状态",
  product: "示例_小程序物卡公版",
})], ctx, { root }).bugs[0];
assert.strictEqual(unrelatedSameProduct.memoryMatch.level, "未命中");

const numericFragment = enrichBugsWithMemory([bug({
  id: "2718",
  title: "电池曲线回落 _1657",
  steps: "观察电量变化",
  expected: "电量曲线稳定",
  actual: "电量回落",
})], ctx, { root }).bugs[0];
assert.ok(!numericFragment.bugFingerprint.codeTokens.includes("_1657"));

const reactivated = enrichBugsWithMemory([bug({ reactivated: true })], ctx, { root }).bugs[0];
assert.strictEqual(reactivated.memoryMatch.level, "高");
assert.strictEqual(reactivated.repairEligibility.label, "复测激活-需重新定位");
assert.strictEqual(reactivated.repairEligibility.directCandidate, false);

const index = require("./memory_linkage").loadMemoryIndex(root);
const managed = index.notes.find((note) => note.fixId === "FP-SYNTHETIC");
assert.strictEqual(managed.verification, "verified");

fs.rmSync(root, { recursive: true, force: true });
console.log("memory_linkage tests passed");
