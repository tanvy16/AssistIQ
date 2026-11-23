import { useTheme } from "../context/ThemeContext";

export type ChartColors = {
  accent: string;
  teal: string;
  violet: string;
  orange: string;
  yellow: string;
  coral: string;
  ink: string;
  muted: string;
  subtle: string;
  grid: string;
  border: string;
  tooltipBg: string;
  series: string[];
};

const DARK: ChartColors = {
  accent: "#65D69A",
  teal: "#62C8C3",
  violet: "#B5A0FF",
  orange: "#F5A65B",
  yellow: "#E7C66A",
  coral: "#F17C82",
  ink: "#F0F2EE",
  muted: "#A3ADA4",
  subtle: "#7D897F",
  grid: "#303830",
  border: "#303830",
  tooltipBg: "#202520",
  series: ["#B5A0FF", "#62C8C3", "#65D69A", "#F5A65B", "#E7C66A", "#F17C82"],
};

const LIGHT: ChartColors = {
  accent: "#1F7A4D",
  teal: "#0E7A76",
  violet: "#5B3DB8",
  orange: "#B45309",
  yellow: "#8A6910",
  coral: "#B42318",
  ink: "#1A1D1A",
  muted: "#5C655D",
  subtle: "#7D897F",
  grid: "#CDD3CD",
  border: "#CDD3CD",
  tooltipBg: "#FBFBFA",
  series: ["#5B3DB8", "#0E7A76", "#1F7A4D", "#B45309", "#8A6910", "#B42318"],
};

export function chartColorsForTheme(theme: "light" | "dark"): ChartColors {
  return theme === "light" ? LIGHT : DARK;
}

export function useChartColors(): ChartColors {
  const { theme } = useTheme();
  return chartColorsForTheme(theme);
}

export const CHART_HEIGHT = 280;
export const CHART_HEIGHT_COMPACT = 240;
