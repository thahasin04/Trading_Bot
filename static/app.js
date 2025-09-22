const es = new EventSource("/stream");

function renderTable(obj) {
  if (!obj || Object.keys(obj).length === 0) return "<i>No data</i>";
  let html = "<table class='table table-sm table-bordered text-light'>";
  for (let [k, v] of Object.entries(obj)) {
    html += `<tr><th>${k}</th><td>${typeof v === "object" ? JSON.stringify(v) : v}</td></tr>`;
  }
  html += "</table>";
  return html;
}

function renderList(arr, labelKey) {
  if (!arr || arr.length === 0) return "<i>No records</i>";
  let html = "<ul class='list-group list-group-flush'>";
  arr.forEach(item => {
    html += `<li class="list-group-item bg-dark text-light">${labelKey ? item[labelKey] : JSON.stringify(item)}</li>`;
  });
  html += "</ul>";
  return html;
}

es.addEventListener("snapshot", ev => {
  let d = JSON.parse(ev.data);

  if (d.profile.ok) {
    const p = d.profile.data.data;
    document.getElementById("profile").innerHTML = `
      <b>${p.user_name}</b> (${p.user_id})<br>${p.email}<br>
      Broker: ${p.broker}<br>
      Exchanges: ${p.exchanges.join(", ")}<br>
      Products: ${p.products.join(", ")}<br>
      Order Types: ${p.order_types.join(", ")}
    `;
  } else {
    document.getElementById("profile").innerHTML = "❌ " + d.profile.error;
  }

  if (d.funds.ok) {
    document.getElementById("funds").innerHTML = renderTable(d.funds.data.data.equity);
  } else {
    document.getElementById("funds").innerHTML = "❌ " + d.funds.error;
  }

  document.getElementById("positions").innerHTML = d.positions.ok ? renderList(d.positions.data.data, null) : "❌ " + d.positions.error;
  document.getElementById("holdings").innerHTML = d.holdings.ok ? renderList(d.holdings.data.data, "symbol") : "❌ " + d.holdings.error;
  document.getElementById("orders").innerHTML = d.orders.ok ? renderList(d.orders.data.data, "instrument_token") : "❌ " + d.orders.error;
  document.getElementById("trades").innerHTML = d.trades.ok ? renderList(d.trades.data.data, "instrument_token") : "❌ " + d.trades.error;
});

es.addEventListener("botmsg", ev => {
  let d = JSON.parse(ev.data);
  document.getElementById("botmsg").innerHTML = "🤖 " + d.msg;
});

// ---- Order Form ----
document.getElementById("orderForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const symbol = document.getElementById("symbol").value;
  const qty = document.getElementById("qty").value;
  const side = document.getElementById("side").value;

  const res = await fetch("/place_order", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol, qty, side })
  });
  const data = await res.json();
  alert(data.ok ? "✅ Order placed successfully!" : "❌ " + data.error);
});
