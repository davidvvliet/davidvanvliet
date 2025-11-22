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
  const [draggedSquare, setDraggedSquare] = useState<string | null>(null);
  const [validMoves, setValidMoves] = useState<string[]>([]);

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

  const getValidMoves = (fromSquare: string): string[] => {
    const moves = chess.moves({ square: fromSquare as any, verbose: true });
    return moves.map(move => move.to);
  };

  const handleDragStart = (e: React.DragEvent, squareName: string) => {
    const [file, rank] = squareName.split('');
    const row = 8 - parseInt(rank);
    const col = FILES.indexOf(file);
    const square = board[row]?.[col];
    
    if (square) {
      setDraggedSquare(squareName);
      setValidMoves(getValidMoves(squareName));
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', squareName);
    }
  };

  const handleDragOver = (e: React.DragEvent, squareName: string) => {
    if (draggedSquare && validMoves.includes(squareName)) {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
    }
  };

  const handleDrop = (e: React.DragEvent, squareName: string) => {
    e.preventDefault();
    
    if (!draggedSquare) return;

    try {
      const move = chess.move({
        from: draggedSquare,
        to: squareName,
        promotion: 'q'
      });

      if (move) {
        setBoard(chess.board());
      }
    } catch (error) {
      // Invalid move - do nothing
    }

    setDraggedSquare(null);
    setValidMoves([]);
    setSelectedSquare(null);
  };

  const handleDragEnd = () => {
    setDraggedSquare(null);
    setValidMoves([]);
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
        setValidMoves(getValidMoves(squareName));
      }
    } else if (selectedSquare === squareName) {
      // Clicking the same selected square - deselect it
      setSelectedSquare(null);
      setValidMoves([]);
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
          setValidMoves([]);
        } else {
          // Invalid move - deselect or select new square
          const [file, rank] = squareName.split('');
          const row = 8 - parseInt(rank);
          const col = FILES.indexOf(file);
          const square = board[row]?.[col];
          
          if (square) {
            setSelectedSquare(squareName);
            setValidMoves(getValidMoves(squareName));
          } else {
            setSelectedSquare(null);
            setValidMoves([]);
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
          setValidMoves(getValidMoves(squareName));
        } else {
          setSelectedSquare(null);
          setValidMoves([]);
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
          const isDragged = draggedSquare === squareName;
          const isValidMove = validMoves.includes(squareName);

          return (
            <div
              key={`${rowIndex}-${colIndex}`}
              className={`${styles.square} ${styles[squareColor]} ${isSelected ? styles.selected : ''} ${isDragged ? styles.dragging : ''} ${isValidMove ? styles.validMove : ''}`}
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
  );
}

