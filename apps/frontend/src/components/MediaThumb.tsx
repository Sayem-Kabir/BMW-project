"use client";

import Image from "next/image";

/** Spec Phase 13 — next/image wrapper for heatmaps / clip thumbnails. */
export function MediaThumb({
  src,
  alt,
  className,
  width = 640,
  height = 360,
}: {
  src: string;
  alt: string;
  className?: string;
  width?: number;
  height?: number;
}) {
  if (!src) return null;
  // Data URLs and relative API paths work with unoptimized next/image
  return (
    <Image
      src={src}
      alt={alt}
      width={width}
      height={height}
      unoptimized
      className={className}
    />
  );
}
