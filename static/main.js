(() => {
  const sessionNameInput = document.getElementById("sessionName");
  const sessionIdInput = document.getElementById("sessionId");
  const sessionInfo = document.getElementById("sessionInfo");
  const characterInfo = document.getElementById("characterInfo");
  const logEl = document.getElementById("log");
  const choicesEl = document.getElementById("choices");
  const stateEl = document.getElementById("state");
  const diceLogEl = document.getElementById("diceLog");

  let currentSessionId = localStorage.getItem("trpg_session_id") || "";
  let currentCharacterId = "";

  if (currentSessionId) {
    sessionIdInput.value = currentSessionId;
    loadSession(currentSessionId);
  }

  document.getElementById("createSessionBtn").onclick = async () => {
    const name = sessionNameInput.value || "session";
    const resp = await fetch("/api/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, safety: { violence: "low" } }),
    });
    const data = await resp.json();
    if (data.id) {
      setSession(data);
      appendLog("system", `Created session ${data.id}`);
    }
  };

  document.getElementById("loadSessionBtn").onclick = () => {
    const id = sessionIdInput.value.trim();
    if (id) loadSession(id);
  };

  document.getElementById("saveCharacterBtn").onclick = async () => {
    if (!currentSessionId) {
      alert("Create or load a session first.");
      return;
    }
    const payload = {
      session_id: currentSessionId,
      name: document.getElementById("charName").value || "Hero",
      race: document.getElementById("charRace").value,
      clazz: document.getElementById("charClass").value,
      level: Number(document.getElementById("charLevel").value || 1),
      base_stats: {
        STR: Number(document.getElementById("statSTR").value || 10),
        DEX: Number(document.getElementById("statDEX").value || 10),
        CON: Number(document.getElementById("statCON").value || 10),
        INT: Number(document.getElementById("statINT").value || 10),
        WIS: Number(document.getElementById("statWIS").value || 10),
        CHA: Number(document.getElementById("statCHA").value || 10),
      },
      resources: {
        hp: Number(document.getElementById("charHP").value || 10),
        max_hp: Number(document.getElementById("charHP").value || 10),
      },
    };
    const resp = await fetch("/api/character", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (data.id) {
      currentCharacterId = data.id;
      characterInfo.innerText = `Character saved: ${data.name}`;
      appendLog("system", `Character ${data.name} saved.`);
      loadSession(currentSessionId);
    } else {
      characterInfo.innerText = `Error: ${JSON.stringify(data)}`;
    }
  };

  document.getElementById("sendBtn").onclick = async () => {
    if (!currentSessionId) {
      alert("Create or load a session first.");
      return;
    }
    const text = document.getElementById("playerInput").value;
    appendLog("player", text);
    document.getElementById("playerInput").value = "";
    const resp = await fetch("/api/gm/turn", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: currentSessionId, player_input: text }),
    });
    const data = await resp.json();
    if (data.narration) appendLog("gm", data.narration, data.log);
    renderChoices(data.choices || []);
    if (data.state) renderState(data.state);
    loadDiceLog();
  };

  document.getElementById("rollBtn").onclick = async () => {
    const expr = document.getElementById("diceExpr").value || "1d20";
    const resp = await fetch("/api/dice/roll", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expression: expr, session_id: currentSessionId }),
    });
    const data = await resp.json();
    if (data.total !== undefined) {
      appendLog("system", `Roll ${expr} => ${data.total} (${data.breakdown})`);
    } else if (data.error) {
      appendLog("system", `Error rolling dice: ${data.error}`);
    }
    loadDiceLog();
  };

  function renderChoices(choices) {
    choicesEl.innerHTML = "";
    (choices || []).forEach((choice) => {
      const btn = document.createElement("button");
      btn.textContent = choice.text || choice.id;
      btn.onclick = () => sendChoice(choice.id);
      choicesEl.appendChild(btn);
    });
  }

  async function sendChoice(choiceId) {
    const resp = await fetch("/api/gm/turn", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: currentSessionId, selected_choice_id: choiceId }),
    });
    const data = await resp.json();
    if (data.narration) appendLog("gm", data.narration, data.log);
    renderChoices(data.choices || []);
    if (data.state) renderState(data.state);
    loadDiceLog();
  }

  function appendLog(role, text, extra) {
    if (!text) return;
    const div = document.createElement("div");
    div.className = "log-entry";
    div.innerHTML = `<strong>[${role}]</strong> ${text}`;
    if (extra && extra.length) {
      const ul = document.createElement("ul");
      extra.forEach((line) => {
        const li = document.createElement("li");
        li.textContent = line;
        ul.appendChild(li);
      });
      div.appendChild(ul);
    }
    logEl.appendChild(div);
    logEl.scrollTop = logEl.scrollHeight;
  }

  function setSession(session) {
    currentSessionId = session.id;
    sessionIdInput.value = session.id;
    localStorage.setItem("trpg_session_id", session.id);
    sessionInfo.innerHTML = `Session ID: <span class="tag">${session.id}</span>`;
    renderState(servicesStateFromSession(session));
    renderDiceLog(session.dice_logs || []);
  }

  function servicesStateFromSession(session) {
    return {
      session_id: session.id,
      name: session.name,
      characters: (session.characters || []).map((c) => ({
        id: c.id,
        name: c.name,
        hp: c.resources?.hp,
        max_hp: c.derived_stats?.max_hp,
        ac: c.derived_stats?.ac,
        conditions: c.resources?.conditions || [],
      })),
      world_facts: session.save_blob?.world_facts || {},
    };
  }

  async function loadSession(id) {
    const resp = await fetch(`/api/session/${id}`);
    const data = await resp.json();
    if (data.id) {
      setSession(data);
      appendLog("system", `Loaded session ${data.id}`);
    } else if (data.error) {
      appendLog("system", data.error);
    }
  }

  function renderState(state) {
    if (!state) return;
    let html = `<div><strong>${state.name || "Session"}</strong> (${state.session_id})</div>`;
    (state.characters || []).forEach((c) => {
      html += `<div>${c.name || "PC"} — HP ${c.hp}/${c.max_hp || c.hp} | AC ${c.ac || "-"}</div>`;
      if (c.conditions && c.conditions.length) {
        html += `<div>Conditions: ${c.conditions.join(", ")}</div>`;
      }
    });
    const facts = state.world_facts || {};
    const factLines = Object.keys(facts).map((k) => `${k}: ${facts[k]}`);
    if (factLines.length) {
      html += `<div>World: ${factLines.join(" | ")}</div>`;
    }
    stateEl.innerHTML = html;
  }

  function renderDiceLog(entries) {
    diceLogEl.innerHTML = "";
    (entries || []).forEach((e) => {
      const div = document.createElement("div");
      div.textContent = `${e.expression}: ${JSON.stringify(e.result)}`;
      diceLogEl.appendChild(div);
    });
  }

  async function loadDiceLog() {
    if (!currentSessionId) return;
    const resp = await fetch(`/api/session/${currentSessionId}`);
    const data = await resp.json();
    if (data.dice_logs) renderDiceLog(data.dice_logs);
  }
})();
