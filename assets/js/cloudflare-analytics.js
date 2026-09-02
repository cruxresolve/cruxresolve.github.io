(() => {
  "use strict";

  const token = "4caebf87691c4e89" + "a3fd0d76c7f90f83";
  const beacon = document.createElement("script");
  beacon.type = "module";
  beacon.src = "https://static.cloudflareinsights.com/beacon.min.js";
  beacon.dataset.cfBeacon = JSON.stringify({ token });
  document.head.appendChild(beacon);
})();
