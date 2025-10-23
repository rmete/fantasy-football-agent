'use client';

import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';

interface TypewriterStatusProps {
  text: string;
  speed?: number;
}

export function TypewriterStatus({ text, speed = 30 }: TypewriterStatusProps) {
  const [displayedText, setDisplayedText] = useState('');

  useEffect(() => {
    setDisplayedText(''); // Reset when text changes
    let currentIndex = 0;

    const interval = setInterval(() => {
      if (currentIndex <= text.length) {
        setDisplayedText(text.slice(0, currentIndex));
        currentIndex++;
      } else {
        clearInterval(interval);
      }
    }, speed);

    return () => clearInterval(interval);
  }, [text, speed]);

  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground italic animate-pulse">
      <Loader2 className="h-3 w-3 animate-spin" />
      <span>{displayedText}</span>
    </div>
  );
}
