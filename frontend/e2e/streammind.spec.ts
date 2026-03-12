import { test, expect } from "@playwright/test";

// ---------------------------------------------------------------------------
// Helper: clear localStorage so each test starts fresh
// ---------------------------------------------------------------------------
test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
});

// ===========================================================================
// 1. Homepage
// ===========================================================================
test.describe("Homepage", () => {
  test("renders hero section with a movie title", async ({ page }) => {
    await page.goto("/");
    const heroTitle = page.locator("main h1").first();
    await expect(heroTitle).toBeVisible({ timeout: 10_000 });
    const text = await heroTitle.textContent();
    expect(text!.length).toBeGreaterThan(0);

    await page.screenshot({ path: "e2e/screenshots/01-homepage-hero.png", fullPage: false });
  });

  test("renders standard lanes (Trending, Top Rated, New Releases)", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Trending Now")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Top Rated")).toBeVisible();
    await expect(page.getByText("New Releases")).toBeVisible();

    await page.screenshot({ path: "e2e/screenshots/02-homepage-lanes.png", fullPage: true });
  });

  test("renders movie cards inside lanes", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Trending Now")).toBeVisible({ timeout: 10_000 });

    const cards = page.locator("main img[alt]");
    await expect(cards.first()).toBeVisible({ timeout: 5000 });
    const count = await cards.count();
    expect(count).toBeGreaterThan(3);

    await page.screenshot({ path: "e2e/screenshots/03-movie-cards.png" });
  });

  test("search bar is visible with placeholder", async ({ page }) => {
    await page.goto("/");
    const input = page.locator('input[type="text"]');
    await expect(input).toBeVisible({ timeout: 10_000 });
    const placeholder = await input.getAttribute("placeholder");
    expect(placeholder).toContain("Describe what you want to watch");

    await page.screenshot({ path: "e2e/screenshots/04-search-bar.png" });
  });
});

// ===========================================================================
// 2. Navigation
// ===========================================================================
test.describe("Navigation", () => {
  test("navbar shows STREAMMIND brand and nav links", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("STREAMMIND")).toBeVisible();
    // Use the nav-scoped locators for links
    const nav = page.locator("nav");
    await expect(nav.getByRole("link", { name: "Home" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "My List" })).toBeVisible();

    await page.screenshot({ path: "e2e/screenshots/05-navbar.png" });
  });

  test("navigates to history page via My List link", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Trending Now")).toBeVisible({ timeout: 10_000 });
    // Click the nav link specifically
    await page.locator("nav").getByRole("link", { name: "My List" }).click();
    await expect(page).toHaveURL(/\/history/);
    // The page heading says "My List"
    await expect(page.locator("h1")).toHaveText("My List");

    await page.screenshot({ path: "e2e/screenshots/06-history-empty.png" });
  });

  test("navigates back to home from history", async ({ page }) => {
    await page.goto("/history");
    await expect(page.locator("h1")).toHaveText("My List", { timeout: 10_000 });
    await page.locator("nav").getByRole("link", { name: "Home" }).click();
    await expect(page).toHaveURL("/");

    await page.screenshot({ path: "e2e/screenshots/07-back-to-home.png" });
  });
});

// ===========================================================================
// 3. Movie Details Modal
// ===========================================================================
test.describe("Movie Details Modal", () => {
  test("opens modal when clicking a movie card", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Trending Now")).toBeVisible({ timeout: 10_000 });

    // Click the first movie card (the wrapping div handles onClick)
    const firstCard = page.locator("main img[alt]").first();
    await firstCard.click();

    // The modal should appear with "Mark as Watched" button
    await expect(
      page.getByText("Mark as Watched").or(page.getByText("Watched"))
    ).toBeVisible({ timeout: 5000 });

    await page.screenshot({ path: "e2e/screenshots/08-movie-detail-modal.png" });
  });

  test("closes modal with X button", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Trending Now")).toBeVisible({ timeout: 10_000 });

    // Open modal
    await page.locator("main img[alt]").first().click();
    await expect(page.getByText("Mark as Watched")).toBeVisible({ timeout: 5000 });

    // Close via X: the first button inside the fixed overlay is the close button
    await page.locator("div.fixed button").first().click();

    // Modal gone
    await expect(page.getByText("Mark as Watched")).not.toBeVisible({ timeout: 3000 });

    await page.screenshot({ path: "e2e/screenshots/09-modal-closed.png" });
  });

  test("closes modal with Escape key", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Trending Now")).toBeVisible({ timeout: 10_000 });

    await page.locator("main img[alt]").first().click();
    await expect(page.getByText("Mark as Watched")).toBeVisible({ timeout: 5000 });

    await page.keyboard.press("Escape");
    await expect(page.getByText("Mark as Watched")).not.toBeVisible({ timeout: 3000 });

    await page.screenshot({ path: "e2e/screenshots/10-modal-esc-closed.png" });
  });

  test("shows streaming platform buttons in modal", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Trending Now")).toBeVisible({ timeout: 10_000 });

    await page.locator("main img[alt]").first().click();
    await expect(page.getByText("Available to Watch On")).toBeVisible({ timeout: 5000 });

    await page.screenshot({ path: "e2e/screenshots/11-streaming-platforms.png" });
  });
});

// ===========================================================================
// 4. Watch History
// ===========================================================================
test.describe("Watch History", () => {
  test("marks a movie as watched from the modal", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Trending Now")).toBeVisible({ timeout: 10_000 });

    // Open modal
    await page.locator("main img[alt]").first().click();
    await expect(page.getByText("Mark as Watched")).toBeVisible({ timeout: 5000 });

    // Click "Mark as Watched"
    await page.getByText("Mark as Watched").click();

    // Should now say "Watched"
    const watchedBtn = page.locator("div.fixed").getByRole("button", { name: /Watched/ });
    await expect(watchedBtn).toBeVisible();

    await page.screenshot({ path: "e2e/screenshots/12-marked-watched.png" });
  });

  test("watched movies appear on the history page", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Trending Now")).toBeVisible({ timeout: 10_000 });

    // Mark a movie as watched
    await page.locator("main img[alt]").first().click();
    await expect(page.getByText("Mark as Watched")).toBeVisible({ timeout: 5000 });
    await page.getByText("Mark as Watched").click();

    // Close modal
    await page.keyboard.press("Escape");
    await expect(page.getByText("Mark as Watched")).not.toBeVisible({ timeout: 3000 });

    // Navigate to history
    await page.locator("nav").getByRole("link", { name: "My List" }).click();
    await expect(page).toHaveURL(/\/history/);

    // Should show "1 movie watched" and a card
    await expect(page.getByText("1 movie watched")).toBeVisible({ timeout: 5000 });
    await expect(page.locator("main img[alt]").first()).toBeVisible();

    await page.screenshot({ path: "e2e/screenshots/13-history-with-movie.png" });
  });

  test("can unmark watched from modal", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Trending Now")).toBeVisible({ timeout: 10_000 });

    // Mark watched
    await page.locator("main img[alt]").first().click();
    await expect(page.getByText("Mark as Watched")).toBeVisible({ timeout: 5000 });
    await page.getByText("Mark as Watched").click();

    // Verify it says Watched
    const watchedBtn = page.locator("div.fixed").getByRole("button", { name: /Watched/ });
    await expect(watchedBtn).toBeVisible();

    // Unmark
    await watchedBtn.click();
    await expect(page.getByText("Mark as Watched")).toBeVisible();

    await page.screenshot({ path: "e2e/screenshots/14-unwatched.png" });
  });
});

// ===========================================================================
// 5. Search (AI lanes)
// ===========================================================================
test.describe("Search", () => {
  test("search bar accepts text input", async ({ page }) => {
    await page.goto("/");
    const input = page.locator('input[type="text"]');
    await expect(input).toBeVisible({ timeout: 10_000 });
    await input.fill("cyberpunk anime");

    await page.screenshot({ path: "e2e/screenshots/15-search-typed.png" });
  });

  test("discover button is enabled when query is entered", async ({ page }) => {
    await page.goto("/");
    const input = page.locator('input[type="text"]');
    await expect(input).toBeVisible({ timeout: 10_000 });

    const btn = page.getByRole("button", { name: /Discover/ });
    await expect(btn).toBeDisabled();

    await input.fill("sci-fi thriller");
    await expect(btn).toBeEnabled();

    await page.screenshot({ path: "e2e/screenshots/16-discover-enabled.png" });
  });
});

// ===========================================================================
// 6. Hero Section Details
// ===========================================================================
test.describe("Hero Section", () => {
  test("hero has Play and More Info buttons", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("main h1").first()).toBeVisible({ timeout: 10_000 });

    // Scope to the hero area (the first large section, before lanes)
    await expect(page.getByRole("button", { name: "Play" })).toBeVisible();
    // Use exact: true and first() to avoid matching movie card "More info" buttons
    await expect(
      page.getByRole("button", { name: "More Info", exact: true }).first()
    ).toBeVisible();

    await page.screenshot({ path: "e2e/screenshots/17-hero-buttons.png" });
  });

  test("More Info opens the movie details modal for the hero movie", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("main h1").first()).toBeVisible({ timeout: 10_000 });

    const heroTitle = await page.locator("main h1").first().textContent();

    // Click the hero "More Info" button (first exact match)
    await page.getByRole("button", { name: "More Info", exact: true }).first().click();

    // Modal should appear
    await expect(
      page.getByText("Mark as Watched").or(page.getByText("Watched"))
    ).toBeVisible({ timeout: 5000 });

    // Modal should contain hero movie title
    await expect(page.locator("div.fixed").getByText(heroTitle!)).toBeVisible();

    await page.screenshot({ path: "e2e/screenshots/18-hero-modal.png" });
  });
});

// ===========================================================================
// 7. Full page visual snapshot
// ===========================================================================
test("full page visual snapshot", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Trending Now")).toBeVisible({ timeout: 10_000 });
  await page.waitForTimeout(2000);

  await page.screenshot({ path: "e2e/screenshots/19-full-page.png", fullPage: true });
});
