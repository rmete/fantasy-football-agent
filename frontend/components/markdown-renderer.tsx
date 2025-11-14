'use client';

import React from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <div className={cn('prose prose-sm dark:prose-invert max-w-none', className)}>
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={{
        // Headings
        h1: ({ node, ...props }) => (
          <h1 className="text-xl font-bold mt-4 mb-2" {...props} />
        ),
        h2: ({ node, ...props }) => (
          <h2 className="text-lg font-bold mt-3 mb-2" {...props} />
        ),
        h3: ({ node, ...props }) => (
          <h3 className="text-base font-semibold mt-2 mb-1" {...props} />
        ),
        
        // Paragraphs
        p: ({ node, ...props }) => (
          <p className="mb-2 leading-relaxed" {...props} />
        ),
        
        // Lists
        ul: ({ node, ...props }) => (
          <ul className="list-disc list-inside mb-2 space-y-1" {...props} />
        ),
        ol: ({ node, ...props }) => (
          <ol className="list-decimal list-inside mb-2 space-y-1" {...props} />
        ),
        li: ({ node, ...props }) => (
          <li className="ml-2" {...props} />
        ),
        
        // Code
        code: ({ node, inline, className, children, ...props }: any) => {
          if (inline) {
            return (
              <code
                className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono"
                {...props}
              >
                {children}
              </code>
            );
          }
          return (
            <code
              className="block bg-muted p-3 rounded-lg text-sm font-mono overflow-x-auto mb-2"
              {...props}
            >
              {children}
            </code>
          );
        },
        pre: ({ node, ...props }) => (
          <pre className="bg-muted p-3 rounded-lg overflow-x-auto mb-2" {...props} />
        ),
        
        // Blockquotes
        blockquote: ({ node, ...props }) => (
          <blockquote
            className="border-l-4 border-primary pl-4 italic my-2 text-muted-foreground"
            {...props}
          />
        ),
        
        // Links
        a: ({ node, ...props }) => (
          <a
            className="text-primary hover:underline"
            target="_blank"
            rel="noopener noreferrer"
            {...props}
          />
        ),
        
        // Tables
        table: ({ node, ...props }) => (
          <div className="overflow-x-auto mb-2">
            <table className="min-w-full divide-y divide-border" {...props} />
          </div>
        ),
        thead: ({ node, ...props }) => (
          <thead className="bg-muted" {...props} />
        ),
        tbody: ({ node, ...props }) => (
          <tbody className="divide-y divide-border" {...props} />
        ),
        tr: ({ node, ...props }) => (
          <tr className="hover:bg-muted/50" {...props} />
        ),
        th: ({ node, ...props }) => (
          <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider" {...props} />
        ),
        td: ({ node, ...props }) => (
          <td className="px-3 py-2 text-sm" {...props} />
        ),
        
        // Horizontal rule
        hr: ({ node, ...props }) => (
          <hr className="my-4 border-border" {...props} />
        ),
        
        // Strong/Bold
        strong: ({ node, ...props }) => (
          <strong className="font-bold" {...props} />
        ),
        
        // Emphasis/Italic
        em: ({ node, ...props }) => (
          <em className="italic" {...props} />
        ),
        }}
      >
        {content}
      </Markdown>
    </div>
  );
}

