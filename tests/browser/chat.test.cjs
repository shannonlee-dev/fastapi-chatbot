const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const { test } = require("node:test");
const { runInNewContext } = require("node:vm");
const { JSDOM } = require("jsdom");

const script = readFileSync(resolve("app/ui/static/chat.js"), "utf8");
const html = readFileSync(process.env.CHAT_TEST_HTML, "utf8");

function page(t, fetch, coarse = false) {
  const dom = new JSDOM(html, {
    url: "https://chat.test/chat",
    runScripts: "outside-only",
  });
  t.after(() => dom.window.close());
  dom.window.matchMedia = () => ({ matches: coarse });
  dom.window.fetch = fetch;
  dom.window.eval(script);
  const document = dom.window.document;
  const input = document.getElementById("chat-message");
  const form = document.getElementById("chat-form");
  return {
    window: dom.window,
    document,
    input,
    form,
    set(value) {
      input.value = value;
      input.dispatchEvent(new dom.window.Event("input"));
    },
    submit() {
      form.dispatchEvent(new dom.window.Event("submit", { cancelable: true }));
    },
  };
}

function success(answer = "답변") {
  return {
    ok: true,
    json: async () => ({
      chat_exchange_id: 7,
      answer,
      created_at: "2026-10-02T01:02:03Z",
    }),
  };
}

const settle = () => new Promise((done) => setImmediate(done));

test("이모지 1000개를 API와 같은 글자 수로 계산하고 전송한다", async (t) => {
  const sent = [];
  const p = page(t, async (_url, options) => {
    sent.push(JSON.parse(options.body).message);
    return success();
  });
  const question = "😀".repeat(1000);
  p.set(question);
  assert.equal(p.document.getElementById("chat-character-count").textContent, "1000 / 1000");
  assert.ok(p.input.maxLength >= question.length);
  p.submit();
  await settle();
  assert.deepEqual(sent, [question]);
  assert.equal(p.document.querySelector("[data-chat-response]").textContent, "답변");
});

test("1001자와 공백 질문을 차단하고 trim한 질문만 전송한다", async (t) => {
  const sent = [];
  const p = page(t, async (_url, options) => {
    sent.push(JSON.parse(options.body).message);
    return success();
  });
  for (const question of ["😀".repeat(1001), " ", "가".repeat(1001)]) {
    p.set(question);
    p.submit();
    assert.equal(sent.length, 0);
    assert.equal(p.document.getElementById("chat-form-error").hidden, false);
    assert.equal(p.input.value, question);
  }
  p.set("  질문  ");
  p.submit();
  await settle();
  assert.deepEqual(sent, ["질문"]);
});

test("진행 중 중복 전송을 막고 새 draft를 유지하며 답변을 text로 렌더링한다", async (t) => {
  let finish;
  let calls = 0;
  const p = page(t, () => {
    calls += 1;
    return new Promise((resolve) => { finish = resolve; });
  });
  p.set("첫 질문");
  p.submit();
  assert.equal(p.document.getElementById("chat-submit").disabled, true);
  p.set("다음 질문");
  p.submit();
  assert.equal(calls, 1);
  assert.equal(p.document.querySelectorAll(".chat-exchange").length, 1);
  finish(success("<img src=x onerror=alert(1)>"));
  await settle();
  assert.equal(p.input.value, "다음 질문");
  assert.equal(p.document.getElementById("chat-submit").disabled, false);
  assert.equal(p.document.querySelector("[data-chat-response]").textContent, "<img src=x onerror=alert(1)>");
  assert.equal(p.document.querySelector("[data-chat-response] img"), null);
  assert.equal(p.document.querySelector("[data-chat-time]").textContent, "2026-10-02 10:02:03 KST");
  assert.equal(p.document.getElementById("chat-empty-state"), null);
});

test("네트워크 실패 뒤 오류를 표시하고 재전송할 수 있다", async (t) => {
  let calls = 0;
  const p = page(t, async () => {
    if (++calls === 1) throw new Error("내부 네트워크 정보");
    return success();
  });
  p.set("질문");
  p.submit();
  await settle();
  const error = p.document.querySelector("[data-chat-response]");
  assert.equal(error.textContent, "요청을 처리하지 못했습니다.");
  assert.equal(error.getAttribute("role"), "alert");
  assert.equal(p.document.getElementById("chat-submit").disabled, false);
  p.set("다시 질문");
  p.submit();
  await settle();
  assert.equal(calls, 2);
  assert.equal(p.document.querySelectorAll(".chat-exchange").length, 2);
});

test("Desktop Enter는 전송하고 Shift·IME·coarse Enter는 줄바꿈을 유지한다", async (t) => {
  let calls = 0;
  const p = page(t, async () => { calls += 1; return success(); });
  p.set("질문");
  for (const options of [{ shiftKey: true }, { isComposing: true }]) {
    p.input.dispatchEvent(new p.window.KeyboardEvent("keydown", { key: "Enter", cancelable: true, ...options }));
  }
  assert.equal(calls, 0);
  p.input.dispatchEvent(new p.window.KeyboardEvent("keydown", { key: "Enter", cancelable: true }));
  await settle();
  assert.equal(calls, 1);
  const mobile = page(t, async () => { calls += 1; return success(); }, true);
  mobile.set("질문");
  const event = new mobile.window.KeyboardEvent("keydown", { key: "Enter", cancelable: true });
  mobile.input.dispatchEvent(event);
  assert.equal(event.defaultPrevented, false);
  assert.equal(calls, 1);
});

for (const [label, response, expected] of [
  ["안전한 API 오류", { ok: false, json: async () => ({ code: "openai_timeout", detail: "응답 시간이 초과되었습니다." }) }, "응답 시간이 초과되었습니다."],
  ["알 수 없는 오류", { ok: false, json: async () => ({ code: "private_error", detail: "내부 정보" }) }, "요청을 처리하지 못했습니다."],
  ["잘못된 성공 응답", { ok: true, json: async () => ({ answer: "내부 정보" }) }, "요청을 처리하지 못했습니다."],
  ["JSON 파싱 실패", { ok: false, json: async () => { throw new Error("내부 정보"); } }, "요청을 처리하지 못했습니다."],
]) {
  test(`${label}를 안전하게 표시하고 입력 상태를 복구한다`, async (t) => {
    const p = page(t, async () => response);
    p.set("질문");
    p.submit();
    await settle();
    assert.equal(p.document.querySelector("[data-chat-response]").textContent, expected);
    assert.equal(p.document.getElementById("chat-submit").disabled, false);
    assert.equal(p.document.activeElement, p.input);
  });
}

test("BFCache 복원에서 화면을 숨기고 현재 세션 확인을 요청한다", (t) => {
  const p = page(t, async () => success());
  const target = new p.window.EventTarget();
  let reloads = 0;
  runInNewContext(readFileSync(resolve("app/ui/static/page-lifecycle.js"), "utf8"), {
    document: p.document,
    window: {
      addEventListener: target.addEventListener.bind(target),
      location: { reload: () => { reloads += 1; } },
    },
  });
  target.dispatchEvent(new p.window.PageTransitionEvent("pageshow", { persisted: false }));
  assert.equal(reloads, 0);
  assert.equal(p.document.documentElement.classList.contains("page-revalidating"), false);
  target.dispatchEvent(new p.window.PageTransitionEvent("pageshow", { persisted: true }));
  assert.equal(reloads, 1);
  assert.equal(p.document.documentElement.classList.contains("page-revalidating"), true);
});
