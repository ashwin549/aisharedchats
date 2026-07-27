<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Shared Chats</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --bg: #0f1117;
      --surface: #1a1d27;
      --surface2: #222538;
      --border: #2a2d3e;
      --text: #e1e4ed;
      --text-secondary: #8b8fa3;
      --accent: #6c8cff;
      --accent-hover: #8ba6ff;
      --green: #34d399;
      --red: #f87171;
      --radius: 10px;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
      min-height: 100vh;
    }
    .container { max-width: 1100px; margin: 0 auto; padding: 24px 20px; }
    header {
      display: flex; align-items: center; justify-content: space-between;
      padding: 16px 0; border-bottom: 1px solid var(--border); margin-bottom: 28px;
      flex-wrap: wrap; gap: 12px;
    }
    header h1 { font-size: 22px; font-weight: 700; color: #fff; }
    header h1 span { color: var(--accent); }
    header .subtitle { font-size: 13px; color: var(--text-secondary); }
    header .actions { display: flex; gap: 10px; }
    .btn {
      display: inline-flex; align-items: center; gap: 6px;
      padding: 9px 18px; border-radius: var(--radius); border: none;
      font-size: 14px; font-weight: 500; cursor: pointer; text-decoration: none;
      transition: all .15s;
    }
    .btn-primary { background: var(--accent); color: #fff; }
    .btn-primary:hover { background: var(--accent-hover); transform: translateY(-1px); }
    .btn-outline {
      background: transparent; color: var(--text); border: 1px solid var(--border);
    }
    .btn-outline:hover { border-color: var(--accent); color: var(--accent); }
    .btn-sm { padding: 6px 14px; font-size: 13px; }
    .btn-green { background: var(--green); color: #000; }
    .btn-green:hover { filter: brightness(1.1); }
    .stats {
      display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap;
    }
    .stat-card {
      background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
      padding: 18px 22px; flex: 1; min-width: 140px;
    }
    .stat-card .num { font-size: 28px; font-weight: 700; color: #fff; }
    .stat-card .label { font-size: 13px; color: var(--text-secondary); margin-top: 2px; }
    .search-bar {
      width: 100%; padding: 12px 16px; border-radius: var(--radius);
      border: 1px solid var(--border); background: var(--surface);
      color: var(--text); font-size: 15px; margin-bottom: 20px;
    }
    .search-bar:focus { outline: none; border-color: var(--accent); }
    .chat-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 14px;
    }
    .chat-card {
      background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
      padding: 18px; transition: all .15s; cursor: pointer;
      display: flex; flex-direction: column;
    }
    .chat-card:hover { border-color: var(--accent); transform: translateY(-2px); }
    .chat-card .title { font-size: 15px; font-weight: 600; color: #fff; margin-bottom: 8px; line-height: 1.3; }
    .chat-card .meta { display: flex; gap: 12px; font-size: 12px; color: var(--text-secondary); flex-wrap: wrap; }
    .chat-card .meta span { display: flex; align-items: center; gap: 4px; }
    .chat-card .badge {
      display: inline-block; padding: 2px 8px; border-radius: 20px;
      font-size: 11px; font-weight: 500; background: var(--surface2); color: var(--text-secondary);
      margin-top: 10px; align-self: flex-start;
    }
    .empty {
      text-align: center; padding: 60px 20px; color: var(--text-secondary);
    }
    .empty h2 { font-size: 20px; margin-bottom: 8px; color: var(--text); }
    .empty p { font-size: 14px; }
    .flash {
      background: var(--surface); border: 1px solid var(--green); border-radius: var(--radius);
      padding: 12px 16px; margin-bottom: 16px; color: var(--green); font-size: 14px;
    }
    .flash.error { border-color: var(--red); color: var(--red); }

    /* Markdown rendering */
    .markdown {
      background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
      padding: 28px 32px; max-width: 100%; overflow-x: auto; line-height: 1.7;
    }
    .markdown h1 { font-size: 26px; margin: 0 0 16px; color: #fff; border-bottom: 1px solid var(--border); padding-bottom: 12px; }
    .markdown h2 { font-size: 20px; margin: 24px 0 12px; color: #fff; }
    .markdown p { margin: 8px 0; }
    .markdown hr { border: none; border-top: 1px solid var(--border); margin: 20px 0; }
    .markdown strong { color: #fff; }
    .markdown blockquote {
      border-left: 3px solid var(--accent); padding: 8px 16px; margin: 12px 0;
      background: var(--surface2); border-radius: 0 var(--radius) var(--radius) 0; color: var(--text-secondary);
    }
    .markdown code {
      background: var(--surface2); padding: 2px 6px; border-radius: 4px; font-size: 13px;
    }
    .markdown pre {
      background: var(--surface2); padding: 16px; border-radius: var(--radius);
      overflow-x: auto; margin: 12px 0; border: 1px solid var(--border);
    }
    .markdown pre code { background: none; padding: 0; }
    .markdown ul, .markdown ol { padding-left: 24px; margin: 8px 0; }
    .markdown a { color: var(--accent); }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>AI <span>Shared Chats</span></h1>
        <div class="subtitle">
          {{ chats|length }} chat{% if chats|length != 1 %}s{% endif %} stored
          &middot; Last run: {{ now.strftime('%b %d, %Y %H:%M') }}
        </div>
      </div>
      <div class="actions">
        <a href="{{ url_for('add_links') }}" class="btn btn-primary">+ Add Links</a>
        <form action="{{ url_for('api_run') }}" method="POST" style="display:inline">
          <button type="submit" class="btn btn-outline btn-sm">&#9654; Run Now</button>
        </form>
      </div>
    </header>

    <div class="stats">
      <div class="stat-card">
        <div class="num">{{ chats|length }}</div>
        <div class="label">Total Chats</div>
      </div>
      <div class="stat-card">
        <div class="num">{{ chats|selectattr('messageCount')|map(attribute='messageCount')|sum }}</div>
        <div class="label">Total Messages</div>
      </div>
      <div class="stat-card">
        <div class="num">{{ chats|selectattr('author')|rejectattr('author', 'equalto', '')|list|length }}</div>
        <div class="label">With Author</div>
      </div>
    </div>

    <input type="text" class="search-bar" id="search" placeholder="Search chats by title, author, or UUID..." oninput="filterChats()">

    {% if chats %}
    <div class="chat-grid" id="chatGrid">
      {% for chat in chats %}
      <a href="{{ url_for('chat_detail', uuid=chat.id) }}" class="chat-card" data-search="{{ chat.title }} {{ chat.author }} {{ chat.id }}">
        <div class="title">{{ chat.title or 'Untitled' }}</div>
        <div class="meta">
          {% if chat.author %}<span>&#128100; {{ chat.author }}</span>{% endif %}
          {% if chat.created %}<span>&#128197; {{ chat.created }}</span>{% endif %}
          <span>&#128172; {{ chat.messageCount or '?' }} msgs</span>
        </div>
        <span class="badge">{{ chat.id[:8] }}...</span>
      </a>
      {% endfor %}
    </div>
    {% else %}
    <div class="empty">
      <h2>No chats yet</h2>
      <p>Add some Claude share links to get started.</p>
      <br>
      <a href="{{ url_for('add_links') }}" class="btn btn-primary">+ Add Your First Links</a>
    </div>
    {% endif %}
  </div>

  <script>
    function filterChats() {
      const q = document.getElementById('search').value.toLowerCase();
      document.querySelectorAll('.chat-card').forEach(card => {
        card.style.display = card.dataset.search.toLowerCase().includes(q) ? '' : 'none';
      });
    }
  </script>
</body>
</html>
