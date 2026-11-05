import React from "react";
import { Composition, registerRoot, staticFile } from "remotion";
import { getAudioDurationInSeconds } from "@remotion/media-utils";
import { MoneyShort } from "./MoneyShort";

const lengthOf = (file: string) => async () => {
  const seconds = await getAudioDurationInSeconds(staticFile(file));
  return { durationInFrames: Math.max(30, Math.ceil(seconds * 30)) };
};

const piece = (id: string, file: string, which: "card" | "fund") =>
  React.createElement(Composition, {
    id,
    component: MoneyShort,
    durationInFrames: 1800,
    fps: 30,
    width: 1080,
    height: 1920,
    defaultProps: { which },
    calculateMetadata: lengthOf(file),
  });

const Root: React.FC = () =>
  React.createElement(
    React.Fragment,
    null,
    piece("CardShort", "card.mp3", "card"),
    piece("FundShort", "fund.mp3", "fund"),
  );

registerRoot(Root);
