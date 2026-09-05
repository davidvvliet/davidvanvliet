"use client";

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Chess } from 'chess.js';
import Image from 'next/image';
import styles from './ChessBoard.module.css';
import { usePageStore } from '../store/pageStore';

const PIECE_IMAGES: { [key: string]: string } = {
  'wP': '/pawn.png', 'wR': '/rook.png', 'wN': '/knight.png', 'wB': '/bishop.png', 'wQ': '/queen.png', 'wK': '/king.png',
  'bP': '/pawn1.png', 'bR': '/rook1.png', 'bN': '/knight1.png', 'bB': '/bishop1.png', 'bQ': '/queen1.png', 'bK': '/king1.png',
};

const FILES = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
const RANKS = ['8', '7', '6', '5', '4', '3', '2', '1'];

// Lichess random puzzle. The PGN holds initialPly + 1 moves; playing all of
// them gives the puzzle position, and the solution (UCI moves) starts with
// the player's move. Verified against the live endpoint.
const PUZZLE_URL = 'https://lichess.org/api/puzzle/next';
const REPLY_DELAY_MS = 350;

type Puzzle = {
  id: string;
  rating: number;
  solution: string[];   // UCI, e.g. "h4f5", "e7e8q"
  fen: string;          // starting position
  playerColor: 'w' | 'b';
};

type Status = 'loading' | 'playing' | 'solved' | 'freeplay';

export default function ChessBoard() {
  const [chess] = useState(new Chess());
  const [board, setBoard] = useState(chess.board());
  const [selectedSquare, setSelectedSquare] = useState<string | null>(null);
  const [draggedSquare, setDraggedSquare] = useState<string | null>(null);
  const [validMoves, setValidMoves] = useState<string[]>([]);
  const [puzzle, setPuzzle] = useState<Puzzle | null>(null);
  const [status, setStatus] = useState<Status>('loading');
  const [wrongSquare, setWrongSquare] = useState<string | null>(null);
  const solutionIndexRef = useRef(0);
  const puzzleRequest = usePageStore((s) => s.puzzleRequest);
  const handledPuzzleSeqRef = useRef(0);

  const refresh = () => setBoard(chess.board());

  const loadPuzzle = useCallback(async (query = '') => {
    setStatus('loading');
    setSelectedSquare(null);
    setValidMoves([]);
    setWrongSquare(null);
    try {
      const res = await fetch(PUZZLE_URL + query);
      if (!res.ok) throw new Error(String(res.status));
      const data = await res.json();
      const game = new Chess();
      for (const san of (data.game.pgn as string).split(' ')) game.move(san);
      const fen = game.fen();
      chess.load(fen);
      solutionIndexRef.current = 0;
      setPuzzle({
        id: data.puzzle.id,
        rating: data.puzzle.rating,
        solution: data.puzzle.solution,
        fen,
        playerColor: chess.turn(),
      });
      setStatus('playing');
    } catch {
      // Offline or blocked: fall back to free play from the start position.
      chess.reset();
      setPuzzle(null);
      setStatus('freeplay');
    }
    refresh();
  }, [chess]);

  useEffect(() => { loadPuzzle(); }, [loadPuzzle]);

  // Terminal `puzzle` command.
  useEffect(() => {
    if (!puzzleRequest || puzzleRequest.seq === handledPuzzleSeqRef.current) return;
    handledPuzzleSeqRef.current = puzzleRequest.seq;
    loadPuzzle(puzzleRequest.query);
  }, [puzzleRequest, loadPuzzle]);

  const uci = (m: { from: string; to: string; promotion?: string }) => `${m.from}${m.to}${m.promotion ?? ''}`;

  // Single gate for both click and drag. Returns true if the move was made.
  const tryMove = (from: string, to: string): boolean => {
    if (status === 'loading' || status === 'solved') return false;
    if (status === 'freeplay' || !puzzle) {
      try { chess.move({ from, to, promotion: 'q' }); refresh(); return true; } catch { return false; }
    }
    // Puzzle: the move must be legal, then match the solution (or be mate).
    let move;
    try { move = chess.move({ from, to, promotion: 'q' }); } catch { return false; }
    const expected = puzzle.solution[solutionIndexRef.current];
    const matches = uci(move) === expected || uci(move).slice(0, 4) === expected.slice(0, 4);
    if (!matches && !chess.isCheckmate()) {
      chess.undo();
      setWrongSquare(to);
      setTimeout(() => setWrongSquare(null), 500);
      return false;
    }
    refresh();
    solutionIndexRef.current += 1;
    if (solutionIndexRef.current >= puzzle.solution.length || chess.isCheckmate()) {
      setStatus('solved');
      return true;
    }
    // Opponent's reply from the solution.
    const reply = puzzle.solution[solutionIndexRef.current];
    setTimeout(() => {
      try { chess.move({ from: reply.slice(0, 2), to: reply.slice(2, 4), promotion: reply[4] }); } catch { /* shouldn't happen */ }
      solutionIndexRef.current += 1;
      refresh();
      if (solutionIndexRef.current >= puzzle.solution.length) setStatus('solved');
    }, REPLY_DELAY_MS);
    return true;
  };

  // Board orientation: the player's side at the bottom.
  const flipped = puzzle?.playerColor === 'b';
  const rows = flipped ? [...Array(8).keys()].reverse() : [...Array(8).keys()];
  const cols = flipped ? [...Array(8).keys()].reverse() : [...Array(8).keys()];

  const getSquareColor = (row: number, col: number): string => ((row + col) % 2 === 0 ? 'light' : 'dark');
  const getSquareName = (row: number, col: number): string => `${FILES[col]}${RANKS[row]}`;

  const getPiece = (row: number, col: number) => {
    const square = board[row][col];
    if (!square) return null;
    return PIECE_IMAGES[`${square.color}${square.type.toUpperCase()}`];
  };

  const pieceAt = (squareName: string) => {
    const [file, rank] = squareName.split('');
    return board[8 - parseInt(rank)]?.[FILES.indexOf(file)];
  };

  const canPick = (squareName: string) => {
    const sq = pieceAt(squareName);
    if (!sq) return false;
    if (status === 'playing' && puzzle && sq.color !== puzzle.playerColor) return false;
    return true;
  };

  const getValidMoves = (fromSquare: string): string[] =>
    chess.moves({ square: fromSquare as any, verbose: true }).map((m) => m.to);

  const select = (squareName: string) => {
    if (canPick(squareName)) {
      setSelectedSquare(squareName);
      setValidMoves(getValidMoves(squareName));
    } else {
      setSelectedSquare(null);
      setValidMoves([]);
    }
  };

  const handleDragStart = (e: React.DragEvent, squareName: string) => {
    if (!canPick(squareName)) { e.preventDefault(); return; }
    setDraggedSquare(squareName);
    setValidMoves(getValidMoves(squareName));
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', squareName);
  };

  const handleDragOver = (e: React.DragEvent, squareName: string) => {
    if (draggedSquare && validMoves.includes(squareName)) {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
    }
  };

  const handleDrop = (e: React.DragEvent, squareName: string) => {
    e.preventDefault();
    if (draggedSquare) tryMove(draggedSquare, squareName);
    setDraggedSquare(null);
    setValidMoves([]);
    setSelectedSquare(null);
  };

  const handleDragEnd = () => {
    setDraggedSquare(null);
    setValidMoves([]);
  };

  const handleSquareClick = (squareName: string) => {
    if (!selectedSquare) { select(squareName); return; }
    if (selectedSquare === squareName) { setSelectedSquare(null); setValidMoves([]); return; }
    if (tryMove(selectedSquare, squareName)) {
      setSelectedSquare(null);
      setValidMoves([]);
    } else {
      select(squareName);
    }
  };

  const sideToMove = puzzle?.playerColor === 'b' ? 'Black' : 'White';
  const statusText =
    status === 'loading' ? 'Loading puzzle...' :
    status === 'freeplay' ? 'Free play' :
    status === 'solved' ? 'Solved' :
    `${sideToMove} to move`;

  return (
    <div className={styles.wrapper}>
      <div className={styles.status}>
        <span className={status === 'solved' ? styles.statusSolved : ''}>{statusText}</span>
        {puzzle && <span className={styles.statusDim}>{puzzle.rating}</span>}
        {status !== 'loading' && (
          <button type="button" className={styles.next} onClick={() => loadPuzzle()}>next</button>
        )}
      </div>
      <div className={styles.chessBoard}>
        {rows.map((rowIndex) =>
          cols.map((colIndex) => {
            const squareColor = getSquareColor(rowIndex, colIndex);
            const squareName = getSquareName(rowIndex, colIndex);
            const piece = getPiece(rowIndex, colIndex);
            const isSelected = selectedSquare === squareName;
            const isDragged = draggedSquare === squareName;
            const isValidMove = validMoves.includes(squareName);
            const isWrong = wrongSquare === squareName;

            return (
              <div
                key={`${rowIndex}-${colIndex}`}
                className={`${styles.square} ${styles[squareColor]} ${isSelected ? styles.selected : ''} ${isDragged ? styles.dragging : ''} ${isValidMove ? styles.validMove : ''} ${isWrong ? styles.wrong : ''}`}
                data-square={squareName}
                onClick={() => handleSquareClick(squareName)}
                onDragOver={(e) => handleDragOver(e, squareName)}
                onDrop={(e) => handleDrop(e, squareName)}
              >
                {piece && (
                  <Image
                    src={piece}
                    alt="chess piece"
                    width={32}
                    height={32}
                    className={styles.piece}
                    draggable={true}
                    onDragStart={(e) => handleDragStart(e, squareName)}
                    onDragEnd={handleDragEnd}
                  />
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
