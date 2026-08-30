window.LUMINIFERA_UI_CONFIG = {
  branding: {
    productName: "Luminifera",
    subtitle: "AI operating space"
  },

  // BACKGROUND MEDIA
  // type: "image" | "video" | "none"
  // For video use .mp4 or .webm. `poster` is optional.
  background: {
    type: "image",
    src: "/assets/v3/assets/background.jpg",
    poster: null,
    overlay: 0.48
  },

  // IRIS MEDIA
  // type: "image" | "video"
  // Example video:
  // { type:"video", src:"assets/iris-idle.webm", poster:"assets/iris.png", autoplay:true, loop:true, muted:true }
  iris: {
    type: "image",
    src: "/assets/v3/assets/iris.png",
    poster: null,
    autoplay: true,
    loop: true,
    muted: true
  },

  ui: {
    reducedMotion: false
  }
};
