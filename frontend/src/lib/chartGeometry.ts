export type ChartSegment = {
  label: string;
  value: number;
  color: string;
};

export type PolarSegment = ChartSegment & {
  d: string;
  startAngle: number;
  endAngle: number;
};

function polar(cx: number, cy: number, radius: number, angle: number): [number, number] {
  const radians = ((angle - 90) * Math.PI) / 180;
  return [cx + radius * Math.cos(radians), cy + radius * Math.sin(radians)];
}

export function donutSegments(
  items: ChartSegment[],
  cx = 50,
  cy = 50,
  outer = 40,
  inner = 24,
): PolarSegment[] {
  const total = items.reduce((sum, item) => sum + Math.max(item.value, 0), 0);
  if (total <= 0) return [];

  let cursor = 0;
  return items
    .filter((item) => item.value > 0)
    .map((item) => {
      const sweep = (item.value / total) * 360;
      const startAngle = cursor;
      const endAngle = cursor + sweep;
      cursor = endAngle;
      const largeArc = sweep > 180 ? 1 : 0;
      const [sx, sy] = polar(cx, cy, outer, startAngle);
      const [ex, ey] = polar(cx, cy, outer, endAngle);
      const [isx, isy] = polar(cx, cy, inner, endAngle);
      const [iex, iey] = polar(cx, cy, inner, startAngle);
      return {
        ...item,
        startAngle,
        endAngle,
        d: `M ${sx} ${sy} A ${outer} ${outer} 0 ${largeArc} 1 ${ex} ${ey} L ${isx} ${isy} A ${inner} ${inner} 0 ${largeArc} 0 ${iex} ${iey} Z`,
      };
    });
}

export function seriesPath(values: number[], width = 100, height = 36, pad = 2): string {
  if (values.length === 0) return "";
  const max = Math.max(...values, 1);
  const usable = height - pad * 2;
  return values
    .map((value, index) => {
      const x = values.length === 1 ? width / 2 : (index / (values.length - 1)) * width;
      const y = height - pad - (value / max) * usable;
      return `${index === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}

export function barPercents(values: number[]): number[] {
  const max = Math.max(...values, 0);
  if (max <= 0) return values.map(() => 0);
  return values.map((value) => (value / max) * 100);
}
