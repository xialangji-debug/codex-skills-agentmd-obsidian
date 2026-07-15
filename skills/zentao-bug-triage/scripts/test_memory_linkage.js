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

writeNote("cloud-album.md", `# LT52 云相册上传状态修复

## 关键词
云相册、上传失败、album_upload_event

## 适用范围
repo: lt52_XCX_GB_WK
branch: TW18_LT52_TEST

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

const ctx = {
  repo: "D:/XM/lt52_XCX_GB_WK",
  repoName: "lt52_XCX_GB_WK",
  branch: "TW18_LT52_TEST",
};

function bug(overrides = {}) {
  return {
    id: "1001",
    title: "云相册上传失败后页面不恢复",
    steps: "进入云相册，上传图片并断网",
    expected: "上传失败后应该恢复按钮并提示失败",
    actual: "按钮一直处于上传中",
    product: "TW18 LT52",
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
})], { repo: "D:/XM/another", repoName: "another", branch: "customer" }, { root }).bugs[0];
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

const reactivated = enrichBugsWithMemory([bug({ reactivated: true })], ctx, { root }).bugs[0];
assert.strictEqual(reactivated.memoryMatch.level, "高");
assert.strictEqual(reactivated.repairEligibility.label, "复测激活-需重新定位");
assert.strictEqual(reactivated.repairEligibility.directCandidate, false);

fs.rmSync(root, { recursive: true, force: true });
console.log("memory_linkage tests passed");
