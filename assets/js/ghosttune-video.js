(() => {
  "use strict";

  document.querySelectorAll("[data-reel-player]").forEach((player) => {
    const playButton = player.querySelector("[data-reel-play]");
    const frame = player.querySelector("[data-reel-frame]");
    if (!playButton || !frame) return;

    playButton.addEventListener("click", () => {
      const reelUrl = playButton.dataset.reelUrl;
      if (!reelUrl) return;

      const embedUrl = new URL("https://www.facebook.com/plugins/video.php");
      embedUrl.searchParams.set("href", reelUrl);
      embedUrl.searchParams.set("show_text", "false");
      embedUrl.searchParams.set("width", "500");
      embedUrl.searchParams.set("autoplay", "false");

      const iframe = document.createElement("iframe");
      iframe.src = embedUrl.toString();
      iframe.title = "GhostTune Facebook Reel";
      iframe.allow = "autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share";
      iframe.referrerPolicy = "strict-origin-when-cross-origin";
      iframe.setAttribute("allowfullscreen", "");

      frame.replaceChildren(iframe);
      frame.hidden = false;
      playButton.hidden = true;

      if (typeof window.cruxTrack === "function") {
        window.cruxTrack("play_video", {
          video_title: "GhostTune product preview",
          video_provider: "Facebook"
        });
      }
    }, { once: true });
  });
})();
