// Executed by `ego-browser nodejs`. The numeric ID only attaches to a space.
const { id, action, args } = request;
const print = (reply) => console.log("BOSSHUNTER_EGO " + JSON.stringify(reply));

async function dispatch(task) {
    if (action === "check") {
        await task.pages();
        return true;
    }
    if (action === "targets") {
        return (await task.tabs()).filter((tab) => tab.label).map((tab) => ({
            targetId: tab.label, type: "page", url: tab.url, title: tab.title,
        }));
    }
    if (action === "new") {
        const page = await task.newPage();
        try {
            if (args.url !== "about:blank") await go(page, args.url);
            return page.label;
        } catch (error) {
            await page.close().catch(() => {});
            throw error;
        }
    }

    const page = task.page(args.label);
    switch (action) {
        case "close":
            await page.close();
            return true;
        case "navigate":
            await go(page, args.url);
            return true;
        case "evaluate":
            return await page.evaluate(args.expression);
        case "info":
            return await page.evaluate(() => ({ title: document.title, url: location.href, ready: document.readyState }));
        case "scroll":
            return await page.evaluate(({ y, direction }) => {
                if (direction === "top") window.scrollTo(0, 0);
                else if (direction === "bottom") window.scrollTo(0, document.documentElement.scrollHeight);
                else window.scrollBy(0, y);
                return true;
            }, args);
        case "wait":
            await page.waitForLoadState("load", { timeout: args.ms });
            return true;
        case "click":
            await page.click(args.selector, { timeout: 10_000, label: "Use recruitment page control" });
            return true;
        case "click_at": {
            const point = /^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$/.exec(args.selector);
            if (point) await page.mouse.click(Number(point[1]), Number(point[2]), { label: "Use recruitment page control" });
            else await page.click(args.selector, { timeout: 10_000, label: "Use recruitment page control" });
            return true;
        }
        case "files":
            await page.setInputFiles(args.selector, args.files);
            return true;
        case "screenshot":
            if (args.selector) throw new Error("Element screenshots are not supported");
            await page.screenshot({ path: args.path });
            return true;
        case "pdf": {
            const fs = await import("node:fs/promises");
            const result = await page.cdp("Page.printToPDF", { printBackground: true });
            await fs.writeFile(args.path, Buffer.from(result.data, "base64"));
            return true;
        }
        case "type":
            await page.keyboard.insertText(args.text);
            return true;
        case "key":
            await page.keyboard.press(args.chord);
            return true;
        default:
            throw new Error("Unknown task-space browser action");
    }
}

async function go(page, url) {
    try {
        await page.goto(url, { waitUntil: "domcontentloaded", timeout: 20_000 });
    } catch (error) {
        if (!error.committed) throw error;
    }
}

const task = await taskSpace(id);
try {
    print({ value: await dispatch(task) });
} catch (error) {
    // Navigation/selector failures are handled by the existing collectors.
    // User control and stale task spaces must never be treated as a page miss.
    const space = (await listTaskSpaces()).find((entry) => entry.id === id);
    if (space?.ownership !== "agent") print({ unavailable: true });
    else print({ value: null });
}
