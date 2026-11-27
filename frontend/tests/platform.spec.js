import { test, expect } from "@playwright/test";

const fixture = JSON.parse(process.env.MULENET_BROWSER_FIXTURE || "null");
if (!fixture?.backend || !fixture.passwords || !fixture.decisions)
  throw new Error(
    "Real backend fixture is required; no synthetic API substitute",
  );
test.beforeEach(async ({ browserName }, info) => {
  if (browserName !== "chromium")
    throw new Error(
      "This acceptance profile requires the configured Chromium engine",
    );
  fixture.decision = fixture.decisions[info.project.name];
});
async function login(page, role) {
  await page.getByLabel("Username", { exact: true }).fill(role);
  await page
    .getByLabel("Password", { exact: true })
    .fill(fixture.passwords[role]);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Sign out", exact: true }),
  ).toBeVisible();
}
async function navigate(page, name) {
  const nav = page.getByRole("navigation", { name: "Investigator navigation" });
  if (!(await nav.isVisible()))
    await page
      .getByRole("button", { name: "Open navigation", exact: true })
      .click();
  await nav.getByRole("link", { name, exact: true }).click();
}
async function openCase(page) {
  await navigate(page, "Decisions");
  await page
    .getByRole("button", {
      name: `Open decision ${fixture.decision}`,
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("heading", { name: "Observed evidence", exact: true }),
  ).toBeVisible();
}

test("real login, tenant queue, evidence, notes, privileged release and policy audit", async ({
  page,
}, info) => {
  const errors = [],
    leakedUrls = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    if (/[?&](token|access_token)=/.test(request.url()))
      leakedUrls.push(request.url());
  });
  await page.goto("/");
  await login(page, "analyst");
  await expect(page.locator(".research-notice")).toContainText("SIMULATED");
  await expect
    .poll(() => page.locator(".nav-foot").textContent())
    .toContain("Connected");
  await expect(
    page.getByRole("link", { name: "Review policy", exact: true }),
  ).toHaveCount(0);
  await openCase(page);
  await expect(page.locator(".degraded-banner")).toContainText(
    "No substitute model probability",
  );
  await expect(page.locator(".react-flow__node")).not.toHaveCount(0);
  await expect(page.getByLabel("Action", { exact: true })).toBeVisible();
  await expect(
    page
      .getByLabel("Action", { exact: true })
      .getByRole("option", { name: "RELEASE", exact: true }),
  ).toHaveCount(0);
  await page
    .getByLabel("Rationale", { exact: true })
    .fill("Browser analyst reviewed the observed synthetic evidence.");
  await page
    .getByRole("button", { name: "Record review", exact: true })
    .click();
  await expect(page.locator(".case-history")).toContainText(
    "Browser analyst reviewed",
  );
  await page.screenshot({
    path: info.outputPath("case-analyst.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await login(page, "supervisor");
  await openCase(page);
  await page.getByLabel("Action", { exact: true }).selectOption("RELEASE");
  await page
    .getByLabel("Rationale", { exact: true })
    .fill(
      "Browser supervisor released this simulated review after examining evidence.",
    );
  await page
    .getByRole("button", { name: "Record review", exact: true })
    .click();
  await expect(page.locator(".case-summary .status")).toHaveText("RELEASED");
  await navigate(page, "Audit trail");
  await expect(page.locator("table")).toContainText("CASE_RELEASE");
  await navigate(page, "Health & drift");
  await expect(page.locator(".drift-state [role=alert]")).toBeVisible();
  await expect(page.locator(".health-state")).toContainText("false");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await login(page, "admin");
  await navigate(page, "Review policy");
  const previous = Number(
    (await page.locator(".policy-form .meta").textContent()).match(
      /Current version (\d+)/,
    )[1],
  );
  await page
    .getByLabel("Change rationale", { exact: true })
    .fill(
      "Browser admin recorded a reviewed policy version for this synthetic fixture.",
    );
  await page
    .getByRole("button", { name: "Save policy version", exact: true })
    .click();
  await expect(page.locator(".policy-form .meta")).toContainText(
    `Current version ${previous + 1}.`,
  );
  await page.screenshot({
    path: info.outputPath("policy.png"),
    fullPage: true,
  });
  const geometry = await page.evaluate(() => ({
    width: innerWidth,
    document: document.documentElement.scrollWidth,
    persisted: localStorage.length,
    session: Object.keys(sessionStorage).filter((key) =>
      /user|token/i.test(key),
    ),
  }));
  expect(geometry.document).toBeLessThanOrEqual(geometry.width + 1);
  expect(geometry.persisted).toBe(0);
  expect(geometry.session).toEqual([]);
  expect(leakedUrls).toEqual([]);
  expect(errors).toEqual([]);
});

test("auditor is read-only and refresh does not restore a browser-stored credential", async ({
  page,
}) => {
  await page.goto("/");
  await login(page, "auditor");
  await openCase(page);
  await expect(
    page.getByRole("button", { name: "Record review", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByText("Read-only auditor session.", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Sign in", exact: true }),
  ).toBeVisible();
});
