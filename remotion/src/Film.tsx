import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Loop,
  OffthreadVideo,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export const FPS = 30;

export type WordCue = {
  text: string;
  start: number;
  end: number;
};

export type SceneProps = {
  duration: number;
  image: string;
  video: string;
  videoSeconds: number;
  lineEn: string;
  lineVi: string;
  words: WordCue[];
  audio: string;
  audioDelay: number;
};

export type FilmProps = {
  title: string;
  logline: string;
  intro: number;
  outro: number;
  music: string;
  musicVolume: number;
  titleAudio: string;
  fonts: boolean;
  captionMode: "bilingual" | "vi";
  scenes: SceneProps[];
};

export function filmFrames(props: FilmProps): number {
  const intro = Math.max(0, Math.round((props.intro || 0) * FPS));
  const outro = Math.max(0, Math.round((props.outro || 0) * FPS));
  const body = (props.scenes || []).reduce((sum, scene) => {
    return sum + Math.max(1, Math.round((scene.duration || 4) * FPS));
  }, 0);
  return Math.max(1, intro + body + outro);
}

const fontStack = "Kids, Segoe UI, sans-serif";

const Backdrop: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const x = 48 + Math.sin(t * 0.65) * 16;
  const y = 28 + Math.cos(t * 0.45) * 10;
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at ${x}% ${y}%, #9ad8ff 0%, #2d6d84 46%, #102833 100%)`,
      }}
    >
      {[0, 1, 2, 3].map((index) => {
        const drift = Math.sin(t * 0.8 + index * 1.3) * 36;
        return (
          <div
            key={index}
            style={{
              position: "absolute",
              width: 160 + index * 50,
              height: 160 + index * 50,
              borderRadius: "50%",
              left: 40 + index * 230,
              top: 160 + index * 300 + drift,
              background: index % 2 === 0 ? "rgba(255, 225, 74, 0.28)" : "rgba(255, 255, 255, 0.14)",
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

const TitleCard: React.FC<{ kicker: string; title: string; logline: string }> = ({ kicker, title, logline }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 14, mass: 0.7 } });
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", padding: 80 }}>
      <div
        style={{
          opacity: enter,
          transform: `translateY(${(1 - enter) * 36}px)`,
          textAlign: "center",
          fontFamily: fontStack,
          color: "#fff8ec",
        }}
      >
        <div style={{ letterSpacing: 4, fontSize: 28, color: "#ffe14a", fontWeight: 700 }}>{kicker}</div>
        <div style={{ fontSize: 72, fontWeight: 700, lineHeight: 1.15, marginTop: 18 }}>{title}</div>
        {logline ? (
          <div style={{ fontSize: 32, lineHeight: 1.4, marginTop: 28, color: "#e7f6ff" }}>{logline}</div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

const Picture: React.FC<{ scene: SceneProps }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  if (scene.video) {
    const videoFrames = Math.max(1, Math.round((scene.videoSeconds || scene.duration) * fps));
    return (
      <Loop durationInFrames={videoFrames}>
        <OffthreadVideo
          src={staticFile(scene.video)}
          muted
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </Loop>
    );
  }
  const scale = interpolate(frame, [0, Math.max(1, durationInFrames - 1)], [1.04, 1.12], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <Img
      src={staticFile(scene.image)}
      style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${scale})` }}
    />
  );
};

const VietnameseLine: React.FC<{ scene: SceneProps }> = ({ scene }) => {
  const text = scene.lineVi || scene.lineEn;
  const size = Math.max(40, Math.min(54, Math.floor(980 / Math.max(text.length, 16))));
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: 0,
        padding: "120px 56px 72px",
        background: "linear-gradient(transparent, rgba(8, 16, 20, 0.86))",
        textAlign: "center",
        fontFamily: fontStack,
        fontWeight: 700,
        fontSize: size,
        lineHeight: 1.35,
        color: "#fff8ec",
      }}
    >
      {text}
    </div>
  );
};

const SceneCard: React.FC<{ scene: SceneProps; title: string; captionMode: "bilingual" | "vi" }> = ({
  scene,
  title,
  captionMode,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const spokenAt = frame / fps - scene.audioDelay;
  let active = -1;
  scene.words.forEach((word, index) => {
    if (spokenAt + 0.04 >= word.start) {
      active = index;
    }
  });
  const size = Math.max(34, Math.min(54, Math.floor(860 / Math.max(scene.lineEn.length, 12))));
  if (captionMode === "vi") {
    return (
      <AbsoluteFill>
        <Picture scene={scene} />
        <VietnameseLine scene={scene} />
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill>
      <div
        style={{
          height: 168,
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "center",
          padding: "0 48px 16px",
          fontFamily: fontStack,
          fontWeight: 700,
          fontSize: 40,
          color: "#fff8ec",
          textAlign: "center",
        }}
      >
        {title}
      </div>
      <div style={{ flex: 1, margin: "0 36px", borderRadius: 28, overflow: "hidden" }}>
        <Picture scene={scene} />
      </div>
      <div
        style={{
          height: 430,
          padding: "26px 42px 32px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 16,
        }}
      >
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center" }}>
          {scene.words.length > 0 ? (
            scene.words.map((word, index) => (
              <span
                key={`${word.text}-${index}`}
                style={{
                  fontFamily: fontStack,
                  fontWeight: 700,
                  fontSize: size,
                  lineHeight: 1.25,
                  margin: "4px 7px",
                  color: index === active ? "#1a1400" : "#fff8ec",
                  background: index === active ? "#ffe14a" : "transparent",
                  borderRadius: 12,
                  padding: index === active ? "0 8px" : "0",
                }}
              >
                {word.text}
              </span>
            ))
          ) : (
            <span
              style={{
                fontFamily: fontStack,
                fontWeight: 700,
                fontSize: size,
                color: "#fff8ec",
                textAlign: "center",
              }}
            >
              {scene.lineEn}
            </span>
          )}
        </div>
        <div
          style={{
            fontFamily: fontStack,
            fontSize: 32,
            lineHeight: 1.35,
            color: "#e7f6ff",
            textAlign: "center",
          }}
        >
          {scene.lineVi}
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const KidsFilm: React.FC<FilmProps> = ({
  title,
  logline,
  intro,
  outro,
  music,
  musicVolume,
  titleAudio,
  fonts,
  captionMode,
  scenes,
}) => {
  const { fps } = useVideoConfig();
  const introFrames = Math.max(0, Math.round((intro || 0) * fps));
  const outroFrames = Math.max(0, Math.round((outro || 0) * fps));
  let cursor = introFrames;
  return (
    <AbsoluteFill style={{ backgroundColor: "#102833" }}>
      {fonts ? (
        <style>
          {`@font-face { font-family: Kids; src: url("${staticFile("job/segoeui.ttf")}") format("truetype"); font-weight: 400; }
            @font-face { font-family: Kids; src: url("${staticFile("job/segoeuib.ttf")}") format("truetype"); font-weight: 700; }`}
        </style>
      ) : null}
      <Backdrop />
      {introFrames > 0 ? (
        <Sequence from={0} durationInFrames={introFrames}>
          <TitleCard kicker="PHIM NGẮN" title={title} logline={logline} />
        </Sequence>
      ) : null}
      {titleAudio && introFrames > 0 ? (
        <Sequence from={Math.round(0.25 * fps)}>
          <Audio src={staticFile(titleAudio)} />
        </Sequence>
      ) : null}
      {scenes.map((scene, index) => {
        const frames = Math.max(1, Math.round(scene.duration * fps));
        const from = cursor;
        cursor += frames;
        return (
          <React.Fragment key={index}>
            <Sequence from={from} durationInFrames={frames}>
              <SceneCard scene={scene} title={title} captionMode={captionMode || "bilingual"} />
            </Sequence>
            {scene.audio ? (
              <Sequence from={from + Math.round(scene.audioDelay * fps)}>
                <Audio src={staticFile(scene.audio)} />
              </Sequence>
            ) : null}
          </React.Fragment>
        );
      })}
      {outroFrames > 0 ? (
        <Sequence from={cursor} durationInFrames={outroFrames}>
          <TitleCard kicker="HẾT" title={title} logline="" />
        </Sequence>
      ) : null}
      {music ? <Audio src={staticFile(music)} volume={musicVolume || 0.2} /> : null}
    </AbsoluteFill>
  );
};
