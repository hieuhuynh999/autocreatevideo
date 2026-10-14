import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
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
  frames?: number;
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
  reel?: string;
  scenes: SceneProps[];
};

export function sceneFrames(scene: SceneProps): number {
  if (scene.frames && scene.frames > 0) {
    return scene.frames;
  }
  return Math.max(1, Math.round((scene.duration || 4) * FPS));
}

export function filmFrames(props: FilmProps): number {
  const intro = Math.max(0, Math.round((props.intro || 0) * FPS));
  const outro = Math.max(0, Math.round((props.outro || 0) * FPS));
  const body = (props.scenes || []).reduce((sum, scene) => sum + sceneFrames(scene), 0);
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
    return (
      <OffthreadVideo
        key={scene.video}
        src={staticFile(scene.video)}
        muted
        style={{ width: "100%", height: "100%", objectFit: "cover" }}
      />
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

const Captions: React.FC<{
  scene: SceneProps;
  captionMode: "bilingual" | "vi";
}> = ({ scene, captionMode }) => {
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
  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          padding: "140px 56px 78px",
          background: "linear-gradient(transparent, rgba(8, 16, 20, 0.82))",
          textAlign: "center",
        }}
      >
        {captionMode === "bilingual" ? (
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center" }}>
            {(scene.words.length > 0 ? scene.words : [{ text: scene.lineEn, start: 0, end: 0 }]).map((word, index) => (
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
            ))}
          </div>
        ) : null}
        <div
          style={{
            marginTop: captionMode === "bilingual" ? 10 : 0,
            fontFamily: fontStack,
            fontWeight: 700,
            fontSize: captionMode === "bilingual" ? 32 : Math.max(40, Math.min(54, Math.floor(980 / Math.max((scene.lineVi || scene.lineEn).length, 16)))),
            lineHeight: 1.35,
            color: captionMode === "bilingual" ? "#e7f6ff" : "#fff8ec",
          }}
        >
          {scene.lineVi || scene.lineEn}
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
  reel,
  scenes,
}) => {
  const { fps } = useVideoConfig();
  const introFrames = Math.max(0, Math.round((intro || 0) * fps));
  const outroFrames = Math.max(0, Math.round((outro || 0) * fps));
  let cursor = introFrames;
  const placed = scenes.map((scene) => {
    const frames = scene.frames && scene.frames > 0 ? scene.frames : Math.max(1, Math.round(scene.duration * fps));
    const from = cursor;
    cursor += frames;
    return { scene, frames, from };
  });
  const bodyFrames = Math.max(1, cursor - introFrames);
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
      {reel ? (
        <Sequence from={introFrames} durationInFrames={bodyFrames}>
          <OffthreadVideo
            src={staticFile(reel)}
            muted
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </Sequence>
      ) : (
        placed.map(({ scene, frames, from }, index) => (
          <Sequence key={scene.video || scene.image || index} from={from} durationInFrames={frames}>
            <Picture scene={scene} />
          </Sequence>
        ))
      )}
      {placed.map(({ scene, frames, from }, index) => (
        <Sequence key={`caption-${index}`} from={from} durationInFrames={frames}>
          <Captions scene={scene} captionMode={captionMode || "bilingual"} />
        </Sequence>
      ))}
      {placed.map(({ scene, from }, index) => (
        scene.audio ? (
          <Sequence key={`voice-${index}`} from={from + Math.round(scene.audioDelay * fps)}>
            <Audio src={staticFile(scene.audio)} />
          </Sequence>
        ) : null
      ))}
      {outroFrames > 0 ? (
        <Sequence from={cursor} durationInFrames={outroFrames}>
          <TitleCard kicker="HẾT" title={title} logline="" />
        </Sequence>
      ) : null}
      {music ? <Audio src={staticFile(music)} volume={musicVolume || 0.2} /> : null}
    </AbsoluteFill>
  );
};
