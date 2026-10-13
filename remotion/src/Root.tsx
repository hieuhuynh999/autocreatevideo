import React from "react";
import { Composition } from "remotion";
import { FilmProps, KidsFilm, filmFrames } from "./Film";

const defaults: FilmProps = {
  title: "Phim ngắn",
  logline: "",
  intro: 2.6,
  outro: 2.2,
  music: "",
  titleAudio: "",
  fonts: false,
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
