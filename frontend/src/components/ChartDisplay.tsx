'use client';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell,
  AreaChart, Area, Radar, RadarChart, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, ZAxis
} from 'recharts';
import { useState, useRef, useEffect } from 'react';
import { ChartSchema } from '../utils/api-client';

interface ChartDisplayProps {
  schema: ChartSchema;
}

const COLORS = ['#cad2fd', '#c7bc92', '#6c6e79', '#39373d', '#a78bfa', '#fb7185', '#34d399'];
const GRADIENTS = [
  { start: '#cad2fd', end: 'rgba(202, 210, 253, 0.2)' },
  { start: '#c7bc92', end: 'rgba(199, 188, 146, 0.2)' },
  { start: '#6c6e79', end: 'rgba(108, 110, 121, 0.2)' },
  { start: '#a78bfa', end: 'rgba(167, 139, 250, 0.2)' },
];

// Generic Component Registry
const CHART_REGISTRY: Record<string, any> = {
  bar: { wrapper: BarChart, element: Bar, hasAxes: true },
  line: { wrapper: LineChart, element: Line, hasAxes: true },
  area: { wrapper: AreaChart, element: Area, hasAxes: true },
  scatter: { wrapper: ScatterChart, element: Scatter, hasAxes: true },
  pie: { wrapper: PieChart, element: Pie, hasAxes: false, isPolar: false, isDonut: false },
  donut: { wrapper: PieChart, element: Pie, hasAxes: false, isPolar: false, isDonut: true },
  radar: { wrapper: RadarChart, element: Radar, hasAxes: false, isPolar: true }
};

export default function ChartDisplay({ schema }: ChartDisplayProps) {
  if (!schema || !schema.data || schema.data.length === 0) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center p-6 text-center space-y-4">
        <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center">
          <svg className="w-8 h-8 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
        <div>
          <p className="text-xs font-black text-slate-400 uppercase tracking-widest">No Data Available</p>
          <p className="text-[10px] text-slate-600 mt-1 font-medium">Dataset segment empty or processing.</p>
        </div>
      </div>
    );
  }

  const chartType = schema.type?.toLowerCase() || 'bar';

  // If the chart type isn't in our base registry, fallback to scatter (generic point rendering)
  const config = CHART_REGISTRY[chartType] || CHART_REGISTRY['scatter'];

  const WrapperComponent = config.wrapper;
  const DataComponent = config.element;

  const renderGenericChart = () => {
    // Coerce data values to numbers if they look like numbers
    const processedData = schema.data.map(item => {
      const newItem = { ...item };
      for (const k of Object.keys(newItem)) {
        if (typeof newItem[k] === 'string' && !isNaN(Number(newItem[k])) && newItem[k].trim() !== '') {
          newItem[k] = Number(newItem[k]);
        }
      }
      return newItem;
    });

    // Determine data keys based on schema or fallback defaults
    let xKey = schema.xAxis || 'x';
    let yKey = schema.yAxis || 'y';
    
    // Fallback heuristic if keys are missing in the data
    const dataKeys = Object.keys(processedData[0] || {});
    console.log('[ChartDisplay] Rendering with schema:', { 
      type: chartType, 
      xKey, 
      yKey, 
      dataKeys, 
      dataLength: processedData.length 
    });

    if (dataKeys.length > 0) {
      // Robust key matching (case-insensitive)
      const findKey = (target: string) => {
        if (dataKeys.includes(target)) return target;
        const targetLower = target.toLowerCase();
        return dataKeys.find(k => k.toLowerCase() === targetLower) || null;
      };

      const matchedX = findKey(xKey);
      if (matchedX) xKey = matchedX;
      else xKey = dataKeys[0];

      const matchedY = findKey(yKey);
      if (matchedY) yKey = matchedY;
      else if (dataKeys.length > 1) {
         // Try to find a numeric key for Y if the requested one didn't match
         const numericKey = dataKeys.find(k => typeof processedData[0][k] === 'number');
         yKey = numericKey || dataKeys[1];
      }
    }

    // Render for Cartesian coordinate charts (Bar, Line, Area, Scatter)
    if (config.hasAxes) {
      const isScatter = chartType === 'scatter';
      return (
        <ResponsiveContainer width="100%" height="100%">
          <WrapperComponent data={processedData} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey={xKey}
              type={isScatter ? 'number' : 'category'}
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#94a3b8', fontSize: 11, fontWeight: 500 }}
              dy={10}
            />
            <YAxis
              dataKey={isScatter ? yKey : undefined}
              type="number"
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#94a3b8', fontSize: 11, fontWeight: 500 }}
            />
            <Tooltip
              contentStyle={{ 
                backgroundColor: 'rgba(15, 23, 42, 0.95)', 
                border: '1px solid rgba(255,255,255,0.12)', 
                borderRadius: '20px',
                backdropFilter: 'blur(16px)',
                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
                padding: '12px 16px'
              }}
              itemStyle={{ color: '#f8fafc', fontWeight: '800', fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.05em' }}
              labelStyle={{ color: '#94a3b8', fontWeight: 'bold', fontSize: '11px', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.1em' }}
              cursor={isScatter ? { strokeDasharray: '3 3' } : { fill: 'rgba(99, 102, 241, 0.08)' }}
            />
            <DataComponent
              dataKey={yKey}
              name={schema.title || yKey}
              fill={schema.fill || "url(#chartGradient)"}
              stroke={schema.stroke || "#6366f1"}
              strokeWidth={chartType === 'line' ? 3 : 1}
              radius={[6, 6, 0, 0]}
              animationDuration={1500}
              animationEasing="ease-in-out"
              {...(schema.extraProps || {})}
            >
              {chartType === 'bar' && processedData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} fillOpacity={0.9} />
              ))}
            </DataComponent>
          </WrapperComponent>
        </ResponsiveContainer>
      );
    }

    // Render for Polar coordinate charts (Radar)
    if (config.isPolar) {
      return (
        <ResponsiveContainer width="100%" height="100%">
          <WrapperComponent data={processedData}>
            <PolarGrid stroke="rgba(255,255,255,0.1)" />
            <PolarAngleAxis dataKey={xKey} tick={{ fill: '#94a3b8', fontSize: 11, fontWeight: 500 }} />
            <PolarRadiusAxis tick={{ fill: '#94a3b8', fontSize: 11, fontWeight: 500 }} />
            <Tooltip
              contentStyle={{ 
                backgroundColor: 'rgba(15, 23, 42, 0.9)', 
                border: '1px solid rgba(255,255,255,0.1)', 
                borderRadius: '16px',
                backdropFilter: 'blur(10px)'
              }}
              itemStyle={{ color: '#f8fafc', fontWeight: 'bold', fontSize: '12px' }}
            />
            <DataComponent
              name={schema.title || yKey}
              dataKey={yKey}
              stroke="#6366f1"
              fill="#6366f1"
              fillOpacity={0.6}
              {...(schema.extraProps || {})}
            />
          </WrapperComponent>
        </ResponsiveContainer>
      );
    }

    // Render for Pie/Donut charts
    const defaultInnerRadius = config.isDonut ? 60 : 0;
    const defaultOuterRadius = 90;

    return (
      <ResponsiveContainer width="100%" height="100%">
        <WrapperComponent>
          <DataComponent
            data={processedData}
            dataKey={yKey}
            nameKey={xKey}
            cx="50%"
            cy="50%"
            innerRadius={schema.innerRadius !== undefined ? schema.innerRadius : defaultInnerRadius}
            outerRadius={schema.outerRadius !== undefined ? schema.outerRadius : defaultOuterRadius}
            paddingAngle={4}
            stroke="rgba(15, 23, 42, 0.8)"
            strokeWidth={2}
            {...(schema.extraProps || {})}
          >
            {processedData.map((_, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </DataComponent>
          <Tooltip
            contentStyle={{ 
              backgroundColor: 'rgba(15, 23, 42, 0.9)', 
              border: '1px solid rgba(255,255,255,0.1)', 
              borderRadius: '16px',
              backdropFilter: 'blur(10px)'
            }}
            itemStyle={{ color: '#f8fafc', fontWeight: 'bold', fontSize: '12px' }}
          />
          <Legend verticalAlign="bottom" iconType="circle" />
        </WrapperComponent>
      </ResponsiveContainer>
    );
  };

  return (
    <div className="w-full h-full flex flex-col">
      <svg width={0} height={0} className="absolute">
        <defs>
          <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#cad2fd" stopOpacity={0.8}/>
            <stop offset="95%" stopColor="#cad2fd" stopOpacity={0}/>
          </linearGradient>
          {COLORS.map((color, i) => (
            <linearGradient key={`grad-${i}`} id={`grad-${i}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.9}/>
              <stop offset="95%" stopColor={color} stopOpacity={0.4}/>
            </linearGradient>
          ))}
        </defs>
      </svg>
      <div className="flex-1 min-h-0">
        {renderGenericChart()}
      </div>
    </div>
  );
}
