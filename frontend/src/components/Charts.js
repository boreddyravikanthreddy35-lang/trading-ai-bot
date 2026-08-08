import React, { useEffect, useRef } from "react";
import { createChart, CandlestickSeries, LineSeries, HistogramSeries } from "lightweight-charts";

/**
 * PriceChart — lightweight-charts candlestick chart with optional SMA/EMA overlays.
 *
 * props:
 *   candles: [{ time (sec), open, high, low, close, volume }]
 *   overlays: optional { sma_20?: [{time, value}], sma_50?: [{time, value}], ema_12?: [...], ema_26?: [...] }
 *   height: pixel height
 *   showVolume: boolean
 */
export function PriceChart({ candles = [], overlays = {}, height = 420, showVolume = true }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef({});

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { type: "solid", color: "transparent" },
        textColor: "hsl(215 14% 70%)",
        fontFamily: "'IBM Plex Sans', sans-serif",
      },
      localization: { locale: "en-US" },
      grid: {
        vertLines: { color: "hsl(220 14% 14%)" },
        horzLines: { color: "hsl(220 14% 14%)" },
      },
      rightPriceScale: { borderColor: "hsl(220 14% 18%)" },
      timeScale: { borderColor: "hsl(220 14% 18%)", timeVisible: true, secondsVisible: false },
      crosshair: { mode: 1 },
      autoSize: true,
    });
    chartRef.current = chart;

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "hsl(152 62% 45%)",
      downColor: "hsl(0 72% 52%)",
      wickUpColor: "hsl(152 62% 45%)",
      wickDownColor: "hsl(0 72% 52%)",
      borderVisible: false,
    });
    seriesRef.current.candle = candleSeries;

    if (showVolume) {
      const volSeries = chart.addSeries(HistogramSeries, {
        priceScaleId: "vol",
        priceFormat: { type: "volume" },
        color: "hsl(200 92% 55% / 0.6)",
      });
      chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
      seriesRef.current.volume = volSeries;
    }

    // Overlays
    if (overlays.sma_20?.length) {
      const s = chart.addSeries(LineSeries, { color: "hsl(188 92% 60%)", lineWidth: 2, priceLineVisible: false, lastValueVisible: false });
      s.setData(overlays.sma_20);
      seriesRef.current.sma_20 = s;
    }
    if (overlays.sma_50?.length) {
      const s = chart.addSeries(LineSeries, { color: "hsl(38 92% 60%)", lineWidth: 2, priceLineVisible: false, lastValueVisible: false });
      s.setData(overlays.sma_50);
      seriesRef.current.sma_50 = s;
    }
    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = {};
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!seriesRef.current.candle) return;
    const cData = candles.map((c) => ({ time: c.time, open: c.open, high: c.high, low: c.low, close: c.close }));
    seriesRef.current.candle.setData(cData);
    if (seriesRef.current.volume) {
      const vData = candles.map((c) => ({
        time: c.time,
        value: c.volume,
        color: c.close >= c.open ? "hsl(152 62% 45% / 0.4)" : "hsl(0 72% 52% / 0.4)",
      }));
      seriesRef.current.volume.setData(vData);
    }
    if (overlays.sma_20 && seriesRef.current.sma_20) seriesRef.current.sma_20.setData(overlays.sma_20);
    if (overlays.sma_50 && seriesRef.current.sma_50) seriesRef.current.sma_50.setData(overlays.sma_50);

    chartRef.current?.timeScale().fitContent();
  }, [candles, overlays]);

  return <div ref={containerRef} data-testid="coin-price-chart" style={{ width: "100%", height }} />;
}


export function Sparkline({ points = [], stroke = "hsl(188 92% 45%)", height = 36, width = 120 }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      width, height,
      layout: { background: { type: "solid", color: "transparent" }, textColor: "transparent" },
      localization: { locale: "en-US" },
      grid: { vertLines: { visible: false }, horzLines: { visible: false } },
      rightPriceScale: { visible: false },
      leftPriceScale: { visible: false },
      timeScale: { visible: false },
      handleScroll: false, handleScale: false,
      crosshair: { horzLine: { visible: false }, vertLine: { visible: false } },
    });
    const s = chart.addSeries(LineSeries, { color: stroke, lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false });
    chartRef.current = chart;
    seriesRef.current = s;
    return () => { chart.remove(); chartRef.current = null; seriesRef.current = null; };
  }, [width, height, stroke]);

  useEffect(() => {
    if (!seriesRef.current || !points?.length) return;
    // Synthesize UNIX timestamps (seconds) — lightweight-charts requires UTCTimestamp, not integer indexes
    const nowSec = Math.floor(Date.now() / 1000);
    const stepSec = 3600; // 1h spacing (visual only)
    const start = nowSec - stepSec * (points.length - 1);
    const data = points.map((p, i) => ({ time: start + i * stepSec, value: Number(p) }));
    seriesRef.current.setData(data);
    chartRef.current?.timeScale().fitContent();
  }, [points]);

  return <div ref={containerRef} style={{ width, height }} />;
}
