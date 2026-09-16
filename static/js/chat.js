/**
 * ApexDrive AI - Real-time WebSocket Chat Client
 * Handles token streaming, latency telemetry, session management, and benchmarks.
 */

class ApexDriveClient {
  constructor() {
    this.sessionId = null;
    this.socket = null;
    this.isGenerating = false;
    this.currentBubbleElement = null;
    this.accumulatedText = "";
    this.reconnectTimer = null;

    // DOM Elements
    this.messagesContainer = document.getElementById("messages-container");
    this.userInput = document.getElementById("user-input");
    this.chatForm = document.getElementById("chat-form");
    this.sendBtn = document.getElementById("send-btn");
    this.newChatBtn = document.getElementById("new-chat-btn");
    this.clearChatBtn = document.getElementById("clear-chat-btn");
    this.benchmarkBtn = document.getElementById("benchmark-btn");
    this.sessionIdDisplay = document.getElementById("session-id-display");
    this.statusPill = document.getElementById("connection-status-pill");
    this.engineIndicator = document.querySelector(".status-indicator");
    this.benchmarkModal = document.getElementById("benchmark-modal");
    this.closeModalBtn = document.getElementById("close-modal-btn");
    this.benchmarkResults = document.getElementById("benchmark-results");
    this.toggleSidebarBtn = document.getElementById("toggle-sidebar-btn");
    this.sidebar = document.getElementById("sidebar");

    this.init();
  }

  async init() {
    this.setupEventListeners();
    await this.initSession();
    this.connectWebSocket();
  }

  setupEventListeners() {
    // Input input auto-resize & send trigger
    this.userInput.addEventListener("input", () => {
      this.userInput.style.height = "auto";
      this.userInput.style.height = `${Math.min(this.userInput.scrollHeight, 160)}px`;
      this.sendBtn.disabled = this.userInput.value.trim().length === 0 || this.isGenerating;
    });

    this.userInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (!this.sendBtn.disabled) {
          this.handleSendMessage();
        }
      }
    });

    this.chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      if (!this.sendBtn.disabled) {
        this.handleSendMessage();
      }
    });

    // Session controls
    this.newChatBtn.addEventListener("click", () => this.startNewSession());
    this.clearChatBtn.addEventListener("click", () => this.resetCurrentSession());

    // Suggestion chips
    document.querySelectorAll(".chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const prompt = chip.getAttribute("data-prompt");
        if (prompt && !this.isGenerating) {
          this.userInput.value = prompt;
          this.userInput.dispatchEvent(new Event("input"));
          this.handleSendMessage();
        }
      });
    });

    // Benchmark button
    this.benchmarkBtn.addEventListener("click", () => this.runBenchmarkModal());
    this.closeModalBtn.addEventListener("click", () => {
      this.benchmarkModal.classList.add("hidden");
    });

    // Mobile sidebar toggle
    if (this.toggleSidebarBtn) {
      this.toggleSidebarBtn.addEventListener("click", () => {
        this.sidebar.classList.toggle("open");
      });
    }
  }

  async initSession() {
    try {
      const res = await fetch("/api/sessions", { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        this.sessionId = data.session_id;
        this.sessionIdDisplay.textContent = this.sessionId.substring(0, 8) + "...";
        this.messagesContainer.innerHTML = "";
        this.renderMessage("assistant", data.welcome_message);
      }
    } catch (e) {
      console.error("Failed to initialize session:", e);
      this.sessionIdDisplay.textContent = "Offline";
    }
  }

  connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/chat`;

    this.socket = new WebSocket(wsUrl);

    this.socket.onopen = () => {
      console.log("WebSocket connected.");
      this.statusPill.textContent = "Connected";
      this.statusPill.className = "pill pill-connected";
      if (this.reconnectTimer) {
        clearInterval(this.reconnectTimer);
        this.reconnectTimer = null;
      }
    };

    this.socket.onclose = () => {
      console.warn("WebSocket disconnected. Reconnecting in 2s...");
      this.statusPill.textContent = "Disconnected";
      this.statusPill.className = "pill pill-disconnected";
      if (!this.reconnectTimer) {
        this.reconnectTimer = setTimeout(() => this.connectWebSocket(), 2000);
      }
    };

    this.socket.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    this.socket.onmessage = (event) => {
      this.handleSocketMessage(event.data);
    };
  }

  handleSocketMessage(raw) {
    try {
      const msg = JSON.parse(raw);

      switch (msg.type) {
        case "token":
          this.appendStreamDelta(msg.delta);
          break;

        case "end_turn":
          this.finalizeAssistantTurn(msg.full_response, msg.metrics);
          break;

        case "session_reset":
          this.messagesContainer.innerHTML = "";
          this.renderMessage("assistant", msg.welcome_message);
          this.setGenerating(false);
          break;

        case "error":
          this.appendStreamDelta(`\n\n**Error:** ${msg.message}`);
          this.finalizeAssistantTurn(this.accumulatedText, null);
          break;

        case "pong":
          break;

        default:
          console.log("Unhandled WS message:", msg);
      }
    } catch (e) {
      console.error("Failed to parse WS message:", e, raw);
    }
  }

  handleSendMessage() {
    const text = this.userInput.value.trim();
    if (!text || this.isGenerating) return;

    // Render user message
    this.renderMessage("user", text);
    this.userInput.value = "";
    this.userInput.style.height = "auto";
    this.sendBtn.disabled = true;

    // Prepare assistant streaming placeholder
    this.accumulatedText = "";
    this.currentBubbleElement = this.createAssistantPlaceholder();
    this.setGenerating(true);

    // Send payload over WebSocket
    const payload = {
      type: "user_message",
      session_id: this.sessionId,
      content: text,
    };

    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(payload));
    } else {
      this.appendStreamDelta("[Error: Not connected to WebSocket server. Reconnecting...]");
      this.finalizeAssistantTurn(this.accumulatedText, null);
    }
  }

  appendStreamDelta(delta) {
    this.accumulatedText += delta;
    if (this.currentBubbleElement) {
      this.currentBubbleElement.innerHTML = marked.parse(this.accumulatedText);
      this.scrollToBottom();
    }
  }

  finalizeAssistantTurn(fullResponse, metrics) {
    if (this.currentBubbleElement) {
      this.currentBubbleElement.innerHTML = marked.parse(fullResponse || this.accumulatedText);

      // Render Latency Telemetry Pill
      if (metrics) {
        const telemetry = document.createElement("div");
        telemetry.className = "telemetry-pill";
        telemetry.innerHTML = `
          <span class="telemetry-item">⚡ TTFT: <span class="val">${metrics.ttft_ms}ms</span></span>
          <span>•</span>
          <span class="telemetry-item">🚀 <span class="val">${metrics.tokens_per_sec}</span> tok/s</span>
          <span>•</span>
          <span class="telemetry-item">⏱️ Total: <span class="val">${(metrics.total_duration_ms / 1000).toFixed(2)}s</span></span>
        `;
        this.currentBubbleElement.parentElement.appendChild(telemetry);
      }
    }

    this.setGenerating(false);
    this.scrollToBottom();
  }

  createAssistantPlaceholder() {
    const row = document.createElement("div");
    row.className = "message-row assistant";

    const avatar = document.createElement("div");
    avatar.className = "avatar assistant";
    avatar.textContent = "AI";

    const container = document.createElement("div");
    container.className = "bubble-container";

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.innerHTML = '<span class="typing-dots">Thinking...</span>';

    container.appendChild(bubble);
    row.appendChild(avatar);
    row.appendChild(container);

    this.messagesContainer.appendChild(row);
    this.scrollToBottom();
    return bubble;
  }

  renderMessage(role, content) {
    const row = document.createElement("div");
    row.className = `message-row ${role}`;

    const avatar = document.createElement("div");
    avatar.className = `avatar ${role}`;
    avatar.textContent = role === "assistant" ? "AI" : "U";

    const container = document.createElement("div");
    container.className = "bubble-container";

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.innerHTML = typeof marked !== "undefined" ? marked.parse(content) : content;

    container.appendChild(bubble);
    row.appendChild(avatar);
    row.appendChild(container);

    this.messagesContainer.appendChild(row);
    this.scrollToBottom();
  }

  setGenerating(generating) {
    this.isGenerating = generating;
    this.sendBtn.disabled = generating || this.userInput.value.trim().length === 0;
    if (generating) {
      this.engineIndicator.classList.add("streaming");
    } else {
      this.engineIndicator.classList.remove("streaming");
    }
  }

  async startNewSession() {
    if (this.isGenerating) return;
    await this.initSession();
  }

  resetCurrentSession() {
    if (this.isGenerating || !this.sessionId) return;
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(
        JSON.stringify({
          type: "reset_session",
          session_id: this.sessionId,
        })
      );
    }
  }

  async runBenchmarkModal() {
    this.benchmarkModal.classList.remove("hidden");
    this.benchmarkResults.innerHTML = `
      <p class="benchmark-loading" style="color: #60a5fa; font-weight: 500;">
        Running 3 inference passes on local CPU (${document.getElementById("model-label").textContent})...
      </p>
      <p style="font-size: 0.8rem; color: #8b949e; margin-top: 8px;">
        Measuring Time-to-First-Token (TTFT) and token generation throughput...
      </p>
    `;

    try {
      const res = await fetch("/api/benchmark?runs=3", { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        this.benchmarkResults.innerHTML = `
          <div style="margin-bottom: 12px;">
            <strong>Hardware:</strong> Local CPU &bull; <strong>Model:</strong> <code>${data.model}</code>
          </div>
          <div class="benchmark-stat-grid">
            <div class="stat-box">
              <div class="stat-label">Avg Time to First Token</div>
              <div class="stat-value">${data.avg_ttft_ms} ms</div>
            </div>
            <div class="stat-box">
              <div class="stat-label">Avg Throughput</div>
              <div class="stat-value">${data.avg_tokens_per_sec} tok/s</div>
            </div>
            <div class="stat-box">
              <div class="stat-label">Avg Total Turn Time</div>
              <div class="stat-value">${(data.avg_total_duration_ms / 1000).toFixed(2)} s</div>
            </div>
            <div class="stat-box">
              <div class="stat-label">Evaluated Runs</div>
              <div class="stat-value">${data.test_runs} passes</div>
            </div>
          </div>
        `;
      } else {
        this.benchmarkResults.innerHTML = `<p style="color: #ef4444;">Benchmark request failed.</p>`;
      }
    } catch (e) {
      this.benchmarkResults.innerHTML = `<p style="color: #ef4444;">Error running benchmark: ${e.message}</p>`;
    }
  }

  scrollToBottom() {
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }
}

// Instantiate on DOM load
window.addEventListener("DOMContentLoaded", () => {
  window.chatClient = new ApexDriveClient();
});
