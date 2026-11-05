import React from "react";
import { Composition, registerRoot, staticFile } from "remotion";
import { getAudioDurationInSeconds } from "@remotion/media-utils";
import { MoneyShort } from "./MoneyShort";

const lengthOf = (file: string) => async () => {
  const seconds = await getAudioDurationInSeconds(staticFile(file));
  return { durationInFrames: Math.max(30, Math.ceil(seconds * 30)) };
};

const Root: React.FC = () => (
  <>
    <Composition
      id="CardShort"
      component={MoneyShort}
      durationInFrames={1800}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{ which: "card" }}
      calculateMetadata={lengthOf("card.mp3")}
    />
    <Composition
      id="FundShort"
      component={MoneyShort}
      durationInFrames={1800}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{ which: "fund" }}
      calculateMetadata={lengthOf("fund.mp3")}
    />
  </>
);

registerRoot(Root);
