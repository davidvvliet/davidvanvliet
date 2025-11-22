"use client";

import { useState, useEffect } from 'react';
import { Chess } from 'chess.js';
import Image from 'next/image';
import styles from './ChessBoard.module.css';

const PIECE_IMAGES: { [key: string]: string } = {
  'wP': '/pawn.png', 'wR': '/rook.png', 'wN': '/knight.png', 'wB': '/bishop.png', 'wQ': '/queen.png', 'wK': '/king.png',
  'bP': '/pawn1.png', 'bR': '/rook1.png', 'bN': '/knight1.png', 'bB': '/bishop1.png', 'bQ': '/queen1.png', 'bK': '/king1.png',
};

const FILES = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
const RANKS = ['8', '7', '6', '5', '4', '3', '2', '1'];

export default function ChessBoard() {
  const [chess] = useState(new Chess());
  const [board, setBoard] = useState(chess.board());
  const [selectedSquare, setSelectedSquare] = useState<string | null>(null);

  useEffect(() => {
    setBoard(chess.board());
  }, [chess]);

  const getSquareColor = (row: number, col: number): string => {
    return (row + col) % 2 === 0 ? 'light' : 'dark';
  };

  const getSquareName = (row: number, col: number): string => {
    return `${FILES[col]}${RANKS[row]}`;
  };

  const getPiece = (row: number, col: number) => {
    const square = board[row][col];
    if (!square) return null;
    const color = square.color === 'w' ? 'w' : 'b';
    const type = square.type.toUpperCase();
    return PIECE_IMAGES[`${color}${type}`];
  };

  const handleSquareClick = (squareName: string) => {
    if (!selectedSquare) {
      // No square selected - select this square if it has a piece
      const [file, rank] = squareName.split('');
      const row = 8 - parseInt(rank);
      const col = FILES.indexOf(file);
      const square = board[row]?.[col];
      
      if (square) {
        setSelectedSquare(squareName);
      }
    } else {
      // Square already selected - attempt to make a move
      try {
        const move = chess.move({
          from: selectedSquare,
          to: squareName,
          promotion: 'q' // Auto-promote to queen
        });

        if (move) {
          // Move is valid - update board
          setBoard(chess.board());
          setSelectedSquare(null);
        } else {
          // Invalid move - deselect or select new square
          const [file, rank] = squareName.split('');
          const row = 8 - parseInt(rank);
          const col = FILES.indexOf(file);
          const square = board[row]?.[col];
          
          if (square) {
            setSelectedSquare(squareName);
          } else {
            setSelectedSquare(null);
          }
        }
      } catch (error) {
        // Invalid move - deselect or select new square
        const [file, rank] = squareName.split('');
        const row = 8 - parseInt(rank);
        const col = FILES.indexOf(file);
        const square = board[row]?.[col];
        
        if (square) {
          setSelectedSquare(squareName);
        } else {
          setSelectedSquare(null);
        }
      }
    }
  };

  return (
    <div className={styles.chessBoard}>
      {board.map((row, rowIndex) =>
        row.map((_, colIndex) => {
          const squareColor = getSquareColor(rowIndex, colIndex);
          const squareName = getSquareName(rowIndex, colIndex);
          const piece = getPiece(rowIndex, colIndex);
          const isSelected = selectedSquare === squareName;

          return (
            <div
              key={`${rowIndex}-${colIndex}`}
              className={`${styles.square} ${styles[squareColor]} ${isSelected ? styles.selected : ''}`}
              data-square={squareName}
              onClick={() => handleSquareClick(squareName)}
            >
              {piece && (
                <Image
                  src={piece}
                  alt="chess piece"
                  width={32}
                  height={32}
                  className={styles.piece}
                />
              )}
            </div>
          );
        })
      )}
    </div>
  );
}

