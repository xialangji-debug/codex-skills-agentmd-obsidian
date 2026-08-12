"use strict";

const assert = require("assert");
const triage = require("./zentao_bug_snapshot");

const context = {
  repo: "C:/sample/repo",
  repoName: "repo",
  branch: "sample-main",
  commit: "abc123",
  dirty: false,
};

const sample = {
  id: "3526",
  title: "计算机界面向右滑动会有点卡顿",
  url: "https://zentao.example/bug-view-3526.html",
  product: "Sample Product",
  bugType: "UI",
  severity: "3",
  priority: "2",
  status: "active",
  openedDate: "2026-08-01",
  editedDate: "",
  resolvedDate: "",
  assignedDate: "",
  closedDate: "",
  openedBy: "tester",
  assignedTo: "developer",
  steps: "步骤：右滑\n结果：卡顿\n期望：流畅退出",
  stepSections: { steps: "右滑", actual: "卡顿", expected: "流畅退出" },
  actual: "卡顿",
  expected: "流畅退出",
  historyRecords: [],
  activationCount: 0,
  lastActivation: null,
  reactivated: false,
  attachmentLinks: [],
  attachments: [],
  detailFetched: true,
  category: "UI Bug",
  difficulty: "中",
  canHandle: "可以先查",
  handlingBucket: "work",
  handlingLabel: "建议检查",
  handlingAction: "review",
  handlingReason: "当前分支需确认",
  advice: "检查共享手势",
  memoryMatch: null,
  repairEligibility: { label: "需先查代码" },
};

const expectedLabel = "3526 计算机界面向右滑动会有点卡顿";
assert.strictEqual(triage.bugDisplayLabel(sample), expectedLabel);
assert.strictEqual(triage.bugDisplayLabel({ id: "#3533", title: "" }), "3533 标题未获取");

const triageReport = triage.markdownReport(context, [sample]);
assert.ok(triageReport.includes("| Bug（ID + 标题） |"));
assert.ok(triageReport.includes(`| ${expectedLabel} |`));
assert.ok(!triageReport.includes("| ID | 标题 |"));

const chatReport = triage.chatSummaryReport(context, [sample], "C:/snapshot");
assert.ok(chatReport.includes("| Bug（ID + 标题） |"));
assert.ok(chatReport.includes(`| ${expectedLabel} |`));
assert.ok(!chatReport.includes("| ID | 标题 |"));

const workReport = triage.workItemsReport(context, [sample], "C:/snapshot");
assert.ok(workReport.includes(`## ${expectedLabel}`));
assert.ok(!workReport.includes("## Bug #3526"));

const ignored = { ...sample, handlingBucket: "ignored" };
const ignoredReport = triage.ignoredItemsReport(context, [ignored], "C:/snapshot");
assert.ok(ignoredReport.includes("| Bug（ID + 标题） |"));
assert.ok(ignoredReport.includes(`| ${expectedLabel} |`));
assert.ok(ignoredReport.includes(`## ${expectedLabel}`));
assert.ok(!ignoredReport.includes("| ID | 标题 |"));

console.log("zentao bug display label tests passed");
