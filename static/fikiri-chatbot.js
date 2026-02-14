(function () {
  const WIDGET_ID = "fikiri-chatbot-widget";
  if (document.getElementById(WIDGET_ID)) return;

  function createStylesheet(href) {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    document.head.appendChild(link);
  }

  function getScriptTag() {
    const scripts = document.getElementsByTagName("script");
    for (let i = scripts.length - 1; i >= 0; i--) {
      const s = scripts[i];
      if (s.src && s.src.indexOf("fikiri-chatbot.js") !== -1) return s;
    }
    return null;
  }

  function createElement(tag, className) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    return el;
  }

  function safeText(value) {
    return (value || "").toString();
  }

  const scriptTag = getScriptTag();
  const apiUrl = scriptTag && scriptTag.dataset.apiUrl ? scriptTag.dataset.apiUrl : "";
  const apiKey = scriptTag && scriptTag.dataset.apiKey ? scriptTag.dataset.apiKey : "";
  const title = scriptTag && scriptTag.dataset.title ? scriptTag.dataset.title : "Fikiri Assistant";
  const theme = scriptTag && scriptTag.dataset.theme ? scriptTag.dataset.theme : "light";
  const accent = scriptTag && scriptTag.dataset.accent ? scriptTag.dataset.accent : "#0f766e";
  const cssUrl = scriptTag && scriptTag.dataset.css ? scriptTag.dataset.css : "/static/fikiri-chatbot.css";

  if (!apiUrl || !apiKey) {
    console.warn("Fikiri chatbot missing data-api-url or data-api-key");
  }

  createStylesheet(cssUrl);

  const root = createElement("div", "fikiri-chatbot");
  root.id = WIDGET_ID;
  root.setAttribute("data-theme", theme);
  root.style.setProperty("--fikiri-accent", accent);

  const button = createElement("button", "fikiri-chatbot__button");
  button.type = "button";
  button.textContent = "Chat";

  const panel = createElement("div", "fikiri-chatbot__panel");
  const header = createElement("div", "fikiri-chatbot__header");
  const titleEl = createElement("div", "fikiri-chatbot__title");
  titleEl.textContent = title;
  const closeBtn = createElement("button", "fikiri-chatbot__close");
  closeBtn.type = "button";
  closeBtn.textContent = "×";
  header.appendChild(titleEl);
  header.appendChild(closeBtn);

  const log = createElement("div", "fikiri-chatbot__log");
  const inputWrap = createElement("div", "fikiri-chatbot__input");
  const input = createElement("input", "fikiri-chatbot__field");
  input.type = "text";
  input.placeholder = "Ask a question...";
  const sendBtn = createElement("button", "fikiri-chatbot__send");
  sendBtn.type = "button";
  sendBtn.textContent = "Send";
  inputWrap.appendChild(input);
  inputWrap.appendChild(sendBtn);

  panel.appendChild(header);
  panel.appendChild(log);
  panel.appendChild(inputWrap);

  root.appendChild(button);
  root.appendChild(panel);
  document.body.appendChild(root);

  let isOpen = false;
  let conversationId = null;

  function appendMessage(author, text) {
    const msg = createElement("div", "fikiri-chatbot__msg");
    msg.setAttribute("data-author", author);
    msg.textContent = safeText(text);
    log.appendChild(msg);
    log.scrollTop = log.scrollHeight;
  }

  async function sendMessage(text) {
    if (!apiUrl || !apiKey) {
      appendMessage("bot", "Missing chatbot configuration.");
      return;
    }
    appendMessage("user", text);
    try {
      const res = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": apiKey
        },
        body: JSON.stringify({
          query: text,
          conversation_id: conversationId || undefined
        })
      });
      const data = await res.json();
      if (data.conversation_id) conversationId = data.conversation_id;
      appendMessage("bot", data.response || "No response");
    } catch (err) {
      appendMessage("bot", "Sorry, something went wrong.");
    }
  }

  function open() {
    isOpen = true;
    panel.classList.add("is-open");
    input.focus();
  }

  function close() {
    isOpen = false;
    panel.classList.remove("is-open");
  }

  button.addEventListener("click", function () {
    if (isOpen) close();
    else open();
  });

  closeBtn.addEventListener("click", function () {
    close();
  });

  sendBtn.addEventListener("click", function () {
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    sendMessage(text);
  });

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      const text = input.value.trim();
      if (!text) return;
      input.value = "";
      sendMessage(text);
    }
  });
})();
