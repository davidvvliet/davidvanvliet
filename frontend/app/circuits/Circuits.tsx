"use client";

import { useSearchParams } from "next/navigation";
import { BoardDetail, Grid } from "../models/PublishedModels";
import type { Board } from "../models/PublishedModels";

// /circuits: the circuit boards, as /models lays out its models (?board=<name> opens one, with its blocks).
export default function Circuits({ boards }: { boards: Board[] }) {
  const asked = useSearchParams().get("board");
  const board = boards.find((b) => b.board === asked);
  if (board) return <BoardDetail board={board} />;
  const cards = boards.map((b) => ({ key: b.board, href: `/circuits?board=${b.board}`, url: `/circuits/${b.board}.glb`, title: b.title }));
  return (
    <Grid back={{ href: "/models", label: "← models" }} title="Circuits" rows={[cards]} empty="No boards yet.">
      Circuit boards built with my KiCad harness and Opus 5.5: open-source designs, and boards made from reusable
      blocks whose parts and values come from their datasheets. Each board&apos;s design source is in its detailed view.
    </Grid>
  );
}
