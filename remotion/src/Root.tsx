import React from "react";
import { Composition } from "remotion";
import { FilmProps, KidsFilm, filmFrames } from "./Film";

const defaults: FilmProps = {
  title: "Phim ngắn",
  logline: "",
  intro: 0,
  outro: 0,
  music: "",
  musicVolume: 0.2,
  titleAudio: "",
  fonts: false,
  captionMode: "bilingual",
  scenes: [],
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="KidsFilm"
      component={KidsFilm}
      durationInFrames={150}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={defaults}
      calculateMetadata={({ props }) => {
        return {
          durationInFrames: filmFrames(props),
          fps: 30,
          width: 1080,
          height: 1920,
        };
      }}
    />
  );
};
