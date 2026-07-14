import { expect, test } from "@playwright/test";

async function ask(page: import("@playwright/test").Page, question: string) {
  const input = page.getByPlaceholder("请输入想分析的问题");
  await input.fill(question);
  await page.getByRole("button", { name: "发送" }).click();
  await expect(page.getByText("分析完成").last()).toBeVisible();
}

test("问题到图表到仪表盘可追踪 2.1—2.6", async ({ page }) => {
  await page.goto("/query");
  await ask(page, "分析2025年各区平均房价");

  await expect(page.getByText("数据来源与 SQL")).toBeVisible();
  await expect(page.getByText(/最大值：/)).toBeVisible();
  await page.getByRole("button", { name: "查看思考过程" }).click();
  await expect(page.getByText(/趋势与异常检测 Skill/)).toBeVisible();
  await page.getByRole("button", { name: "加入仪表盘" }).click();
  await expect(page.getByText("已加入“房价分析看板”")).toBeVisible();

  await page.getByRole("link", { name: "我的仪表盘" }).click();
  await expect(page.getByRole("heading", { name: "2025年各区房价趋势" })).toBeVisible();
  await expect(page.getByRole("link", { name: "需求 2.6" })).toBeVisible();
});

test("多轮追问继承年份并覆盖区域 2.3", async ({ page }) => {
  await page.goto("/query");
  await ask(page, "分析2025年各区平均房价");
  await ask(page, "只看海淀区");

  await expect(page.getByText(/district = '海淀区'/)).toBeVisible();
  await expect(page.getByRole("link", { name: "需求 2.3" })).toBeVisible();
});

test("多源问题拆为房产和人口通勤两条 SQL 5", async ({ page }) => {
  await page.goto("/query");
  await ask(page, "2025年房价上涨是否与人口和通勤相关");

  await expect(page.getByText("SQL 查询 · 房产数据")).toBeVisible();
  await expect(page.getByText("SQL 查询 · 人口通勤数据")).toBeVisible();
  await expect(page.getByText(/相关性仅表示指标共同变化/)).toBeVisible();
  await expect(page.getByRole("link", { name: "需求 5" })).toBeVisible();
});

test("知识详情显示私有优先和双向数据表关系 3.2/3.4", async ({ page }) => {
  await page.goto("/knowledge");
  await page.getByRole("button", { name: /行政区房价口径，私有/ }).click();

  await expect(page.getByText("私有知识优先")).toBeVisible();
  await expect(page.getByText("公开条目被覆盖")).toBeVisible();
  await expect(page.getByText("双向关联")).toBeVisible();
  await expect(page.getByRole("link", { name: "需求 3.2" })).toBeVisible();
});

test("手动与模拟定时同步共用审计并确认删除联动 3.3", async ({ page }) => {
  await page.goto("/knowledge");
  await page.getByRole("button", { name: "手动同步" }).click();
  await expect(page.getByText(/已完成 4 张演示数据表/)).toBeVisible();
  await page.getByRole("button", { name: "模拟定时同步" }).click();
  await expect(page.getByText(/已完成 4 张演示数据表/)).toBeVisible();

  await page.getByRole("button", { name: "演示删除联动" }).click();
  const dialog = page.getByRole("dialog", { name: "确认删除数据表" });
  await expect(dialog).toContainText("关联知识");
  await dialog.getByRole("button", { name: "确认删除并联动" }).click();
  await expect(page.getByText(/删除联动完成/)).toBeVisible();
  await expect(page.getByRole("link", { name: "需求 3.3" })).toBeVisible();
});
