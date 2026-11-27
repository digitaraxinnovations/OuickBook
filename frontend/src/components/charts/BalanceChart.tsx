"use client";

import { PointerEvent, useEffect, useRef, useState } from "react";
import { appConfig } from "@/config/app.config";
import { formatDate, formatMoney, toNumber } from "@/lib/format";
import { DayBalance } from "@/types/models";

export interface BalanceSeries {
  label: string;
  color: string;
  days: DayBalance[];
}

interface BalanceChartProps {
  series: BalanceSeries[];
  /** Balances under this line are a warning. */
  limit: number;
  currency?: string;
}

const HEIGHT = 280;
const LEFT = 64;
const RIGHT = 12;
const TOP = 12;
const BOTTOM = 28;

/** About four round numbers covering the range. */
function ticks(min: number, max: number): number[] {
  const rough = (max - min) / 4 || 1;
  const power = Math.pow(10, Math.floor(Math.log10(rough)));
  const step = [1, 2, 2.5, 5, 10].map((factor) => factor * power).find((value) => value >= rough) || rough;
  const result = [];
  for (let value = Math.floor(min / step) * step; value <= max + step * 0.999; value += step) {
    result.push(value);
  }
  return result;
}

function shortMoney(value: number, currency?: string): string {
  return new Intl.NumberFormat(appConfig.locale, {
    style: "currency",
    currency: currency || appConfig.defaultCurrency,
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

/** Bank balance over time, one line per series, with a hover read-out. */
export function BalanceChart({ series, limit, currency }: BalanceChartProps) {
  const box = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(720);
  const [hover, setHover] = useState<number | null>(null);

  useEffect(() => {
    const element = box.current;
    if (!element) {
      return;
    }
    const observer = new ResizeObserver((entries) => setWidth(Math.max(entries[0].contentRect.width, 280)));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const dates = series[0].days.map((day) => day.date);
  const values = series.flatMap((line) => line.days.map((day) => toNumber(day.balance)));
  const scale = ticks(Math.min(0, limit, ...values), Math.max(0, ...values));
  const low = scale[0];
  const high = scale[scale.length - 1];

  const x = (index: number) => LEFT + (index / Math.max(dates.length - 1, 1)) * (width - LEFT - RIGHT);
  const y = (value: number) => TOP + ((high - value) / (high - low || 1)) * (HEIGHT - TOP - BOTTOM);
  const path = (days: DayBalance[]) =>
    days.map((day, index) => (index ? "L" : "M") + x(index).toFixed(1) + " " + y(toNumber(day.balance)).toFixed(1)).join(" ");

  // Date labels every few weeks, as many as fit.
  const labelCount = Math.max(2, Math.min(6, Math.floor(width / 120)));
  const labelAt = Array.from({ length: labelCount }, (_, i) => Math.round((i * (dates.length - 1)) / (labelCount - 1)));

  function move(event: PointerEvent<SVGSVGElement>) {
    const position = event.clientX - event.currentTarget.getBoundingClientRect().left;
    const index = Math.round(((position - LEFT) / (width - LEFT - RIGHT)) * (dates.length - 1));
    setHover(Math.max(0, Math.min(dates.length - 1, index)));
  }

  return (
    <div>
      {series.length > 1 && (
        <div className="mb-2 flex gap-4 text-xs text-gray-600">
          {series.map((line) => (
            <span key={line.label} className="flex items-center gap-1.5">
              <span className="inline-block h-0.5 w-4" style={{ background: line.color }} />
              {line.label}
            </span>
          ))}
        </div>
      )}
      <div ref={box} className="relative">
        <svg
          width={width}
          height={HEIGHT}
          role="img"
          aria-label="Expected bank balance by day. The same figures are in the table below."
          onPointerMove={move}
          onPointerLeave={() => setHover(null)}
        >
          {scale.map((value) => (
            <g key={value}>
              <line x1={LEFT} x2={width - RIGHT} y1={y(value)} y2={y(value)} stroke={value === 0 ? "#9ca3af" : "#e5e7eb"} />
              <text x={LEFT - 8} y={y(value) + 4} textAnchor="end" fontSize="11" fill="#6b7280">
                {shortMoney(value, currency)}
              </text>
            </g>
          ))}
          {limit !== 0 && <line x1={LEFT} x2={width - RIGHT} y1={y(limit)} y2={y(limit)} stroke="#dc2626" strokeDasharray="4 4" />}
          {labelAt.map((index, i) => (
            <text key={index} x={x(index)} y={HEIGHT - 8} fontSize="11" fill="#6b7280" textAnchor={i === 0 ? "start" : i === labelCount - 1 ? "end" : "middle"}>
              {formatDate(dates[index]).replace(/, \d{4}$/, "")}
            </text>
          ))}
          {series.map((line) => (
            <path key={line.label} d={path(line.days)} fill="none" stroke={line.color} strokeWidth="2" strokeLinejoin="round" />
          ))}
          {hover !== null && (
            <g>
              <line x1={x(hover)} x2={x(hover)} y1={TOP} y2={HEIGHT - BOTTOM} stroke="#9ca3af" />
              {series.map((line) => (
                <circle key={line.label} cx={x(hover)} cy={y(toNumber(line.days[hover].balance))} r="4" fill={line.color} stroke="white" strokeWidth="2" />
              ))}
            </g>
          )}
        </svg>
        {hover !== null && (
          <div
            className="pointer-events-none absolute top-2 whitespace-nowrap rounded-md border border-gray-200 bg-white px-3 py-2 text-xs shadow-md"
            style={x(hover) > width / 2 ? { right: width - x(hover) + 10 } : { left: x(hover) + 10 }}
          >
            <div className="font-semibold text-gray-900">{formatDate(dates[hover])}</div>
            {series.map((line) => (
              <div key={line.label} className="mt-1 flex items-center gap-2 text-gray-600">
                <span className="inline-block h-2 w-2 rounded-full" style={{ background: line.color }} />
                {line.label}
                <span className="ml-auto pl-3 font-medium text-gray-900">{formatMoney(line.days[hover].balance, currency)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
