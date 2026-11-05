import React, { useLayoutEffect, useRef } from "react";
import { AbsoluteFill, Audio, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Expr, Outfit, Pen, SKIN, bodyFront } from "../../templates/bridge/toon";

const HOST: Outfit = {
  jacket: "#3f6fb5",
  pants: "#3b3f52",
  boots: "#4a3426",
  hat: "hair",
  hair: "#2a2018",
  skin: SKIN,
  build: "adult",
};

type Which = "card" | "fund";

const sceneOf = (which: Which, unit: number): { expr: Expr; prop: string } => {
  if (which === "fund") {
    if (unit < 0.22) return { expr: "neutral", prop: "jars" };
    if (unit < 0.48) return { expr: "nervous", prop: "maybe" };
    if (unit < 0.72) return { expr: "stern", prop: "many" };
    return { expr: "relief", prop: "habit" };
  }
  if (unit < 0.18) return { expr: "neutral", prop: "card" };
  if (unit < 0.38) return { expr: "nervous", prop: "leak" };
  if (unit < 0.58) return { expr: "shock", prop: "scale" };
  if (unit < 0.8) return { expr: "grin", prop: "extra" };
  return { expr: "relief", prop: "habit" };
};

const sky = (ctx: CanvasRenderingContext2D, width: number, height: number) => {
  const paint = ctx.createLinearGradient(0, 0, 0, height * 0.62);
  paint.addColorStop(0, "#3e7fd2");
  paint.addColorStop(1, "#b8d0ec");
  ctx.fillStyle = paint;
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = "#d7c4a4";
  ctx.fillRect(0, height * 0.72, width, height);
};

const coin = (pen: Pen, x: number, y: number, radius: number) => {
  pen.ell(x, y, radius, radius * 0.92, "#f2c14d");
  pen.ell(x, y, radius * 0.55, radius * 0.5, "#ffe7a0", 4);
};

const card = (pen: Pen, x: number, y: number) => {
  pen.poly(
    [
      [x, y],
      [x + 430, y],
      [x + 430, y + 270],
      [x, y + 270],
    ],
    "#245ca8",
  );
  pen.poly(
    [
      [x + 36, y + 40],
      [x + 120, y + 40],
      [x + 120, y + 100],
      [x + 36, y + 100],
    ],
    "#f2c14d",
    6,
  );
  pen.poly(
    [
      [x, y + 130],
      [x + 430, y + 130],
      [x + 430, y + 168],
      [x, y + 168],
    ],
    "#1a1a1a",
    0,
  );
};

const props = (pen: Pen, kind: string, frame: number) => {
  if (kind === "card") card(pen, 560, 280);
  if (kind === "leak") {
    card(pen, 560, 240);
    for (let index = 0; index < 5; index++) coin(pen, 860, 360 + ((frame * 6 + index * 70) % 420), 28);
  }
  if (kind === "scale") {
    pen.poly(
      [
        [620, 520],
        [980, 500],
        [980, 540],
        [620, 560],
      ],
      "#5c5c64",
    );
    pen.poly(
      [
        [640, 560],
        [820, 560],
        [820, 860],
        [640, 860],
      ],
      "#c0392b",
    );
    pen.poly(
      [
        [860, 700],
        [980, 700],
        [980, 860],
        [860, 860],
      ],
      "#2e8b57",
    );
  }
  if (kind === "extra") {
    for (let index = 0; index < 4; index++) coin(pen, 700 + index * 70, 760 - index * 18, 34);
  }
  if (kind === "jars") {
    for (let index = 0; index < 5; index++) {
      const x = 590 + index * 90;
      pen.poly(
        [
          [x, 520],
          [x + 70, 520],
          [x + 70, 860],
          [x, 860],
        ],
        "#d7e7f2",
      );
      pen.poly(
        [
          [x + 8, 860 - (index + 1) * 50],
          [x + 62, 860 - (index + 1) * 50],
          [x + 62, 850],
          [x + 8, 850],
        ],
        "#f2c14d",
        0,
      );
    }
  }
  if (kind === "maybe") {
    for (let index = 0; index < 3; index++) coin(pen, 640 + index * 80, 780, 30);
    pen.ell(900, 420, 70, 70, "#f6f1e4");
  }
  if (kind === "many") {
    for (let index = 0; index < 8; index++) {
      const x = 560 + (index % 4) * 110;
      const y = 300 + Math.floor(index / 4) * 160;
      pen.poly(
        [
          [x, y + 80],
          [x + 40, y],
          [x + 90, y + 80],
        ],
        ["#c47a4a", "#6d8f4e", "#4d79a8", "#b5524a"][index % 4],
      );
    }
  }
  if (kind === "habit") {
    for (let index = 0; index < 3; index++) coin(pen, 650 + index * 110, 700, 36);
  }
};

const paint = (ctx: CanvasRenderingContext2D, frame: number, which: Which, frames: number) => {
  const width = 1080;
  const height = 1920;
  sky(ctx, width, height);
  const pen = new Pen(ctx);
  pen.ol = 8;
  const scene = sceneOf(which, frame / frames);
  props(pen, scene.prop, frame);
  const board = document.createElement("canvas");
  board.width = 600;
  board.height = 1000;
  const local = board.getContext("2d");
  if (!local) return;
  bodyFront(new Pen(local), HOST, {
    phase: (frame % 48) / 48,
    expr: scene.expr,
    mode: "stroll",
    light: -1.15,
    seed: 4,
  });
  ctx.drawImage(board, 40, 760, 500, 833);
};

export const MoneyShort: React.FC<{ which: Which }> = ({ which }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const ref = useRef<HTMLCanvasElement>(null);
  useLayoutEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    paint(ctx, frame, which, durationInFrames);
  }, [frame, which, durationInFrames]);
  return (
    <AbsoluteFill style={{ background: "#b8d0ec" }}>
      <canvas ref={ref} width={1080} height={1920} />
      <Audio src={staticFile(which === "fund" ? "fund.mp3" : "card.mp3")} />
    </AbsoluteFill>
  );
};
