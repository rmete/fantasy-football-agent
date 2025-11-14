'use client';

import React, { useState } from 'react';
import Image from 'next/image';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Camera, X } from 'lucide-react';
import type { Screenshot } from '@/types/agent';

interface ScreenshotStripProps {
  screenshots: Screenshot[];
}

export function ScreenshotStrip({ screenshots }: ScreenshotStripProps) {
  const [selectedScreenshot, setSelectedScreenshot] = useState<Screenshot | null>(null);

  if (screenshots.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-muted-foreground text-sm bg-muted/30 rounded-lg border border-dashed">
        <div className="flex flex-col items-center gap-2">
          <Camera className="h-6 w-6 opacity-50" />
          <span>No screenshots yet</span>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="overflow-x-auto pb-2">
        <div className="flex gap-3 min-w-max">
          {screenshots.map((screenshot) => (
            <button
              key={screenshot.id}
              onClick={() => setSelectedScreenshot(screenshot)}
              className="relative group flex-shrink-0 w-48 h-32 rounded-lg overflow-hidden border border-border hover:border-primary transition-all hover:shadow-md"
            >
              {/* Thumbnail Image */}
              <div className="relative w-full h-full bg-muted">
                <Image
                  src={screenshot.url}
                  alt={screenshot.tag || 'Screenshot'}
                  fill
                  className="object-cover"
                  sizes="(max-width: 768px) 192px, 192px"
                />
              </div>

              {/* Overlay on Hover */}
              <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                <div className="text-white text-sm font-medium">Click to enlarge</div>
              </div>

              {/* Tag Badge */}
              {screenshot.tag && (
                <div className="absolute top-2 left-2">
                  <Badge variant="secondary" className="text-xs bg-black/70 text-white border-none">
                    {screenshot.tag}
                  </Badge>
                </div>
              )}

              {/* Timestamp */}
              <div className="absolute bottom-2 right-2">
                <Badge variant="secondary" className="text-xs bg-black/70 text-white border-none">
                  {new Date(screenshot.timestamp).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </Badge>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Full-size Modal */}
      <Dialog open={!!selectedScreenshot} onOpenChange={() => setSelectedScreenshot(null)}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-auto">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <DialogTitle>
                {selectedScreenshot?.tag || 'Screenshot'}
                {selectedScreenshot?.timestamp && (
                  <span className="text-sm font-normal text-muted-foreground ml-2">
                    {new Date(selectedScreenshot.timestamp).toLocaleString()}
                  </span>
                )}
              </DialogTitle>
            </div>
          </DialogHeader>

          {selectedScreenshot && (
            <div className="relative w-full min-h-[400px] bg-muted rounded-lg overflow-hidden">
              <Image
                src={selectedScreenshot.url}
                alt={selectedScreenshot.tag || 'Screenshot'}
                width={1920}
                height={1080}
                className="w-full h-auto"
                unoptimized
              />
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
