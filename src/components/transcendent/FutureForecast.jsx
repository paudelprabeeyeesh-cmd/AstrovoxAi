import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { forecastEvent, getTrendAnalysis } from '../../services/predictionService'

export default function FutureForecast({ eventType = 'system_load' }) {
  const [forecasts, setForecasts] = useState([])
  const [trend, setTrend] = useState(null)

  useEffect(() => {
    const loadForecasts = async () => {
      try {
        const context = { trend_direction: 'stable', data_quality: 'high', volatility: 0.3 }
        const data = await forecastEvent(eventType, context, '7d')
        setForecasts(data.forecasts || [])
        const trendData = await getTrendAnalysis(eventType, '30d')
        setTrend(trendData)
      } catch (e) {
        console.error('Forecasting failed:', e)
      }
    }
    loadForecasts()
    const interval = setInterval(loadForecasts, 30000)
    return () => clearInterval(interval)
  }, [eventType])

  return (
    <div style={{
      backgroundColor: 'rgba(4,8,20,0.6)',
      border: '1px solid #1e293b',
      borderRadius: '12px',
      padding: '16px'
    }}>
      <h3 style={{
        margin: '0 0 12px',
        fontSize: '13px',
        color: '#f59e0b',
        textTransform: 'uppercase',
        letterSpacing: '1px'
      }}>
        📈 Future Event Forecast
      </h3>
      {trend && (
        <div style={{
          padding: '8px 12px',
          backgroundColor: 'rgba(6,182,212,0.05)',
          borderRadius: '6px',
          marginBottom: '8px',
          fontSize: '11px',
          color: '#94a3b8'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>Trend:</span>
            <span style={{ color: '#22c55e' }}>{trend.trend}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>Confidence:</span>
            <span style={{ color: '#f59e0b' }}>{(trend.confidence * 100).toFixed(0)}%</span>
          </div>
        </div>
      )}
      <AnimatePresence>
        {forecasts.map((forecast, idx) => (
          <motion.div
            key={forecast.forecast_id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            style={{
              padding: '8px 12px',
              backgroundColor: 'rgba(6,182,212,0.05)',
              borderRadius: '6px',
              marginBottom: '4px',
              fontSize: '11px',
              color: '#94a3b8'
            }}
          >
            <div style={{ fontSize: '12px', color: '#e2e8f0', marginBottom: '2px' }}>
              {forecast.prediction}
            </div>
            <div style={{ display: 'flex', gap: '12px', fontSize: '10px', color: '#64748b' }}>
              <span>Probability: {(forecast.probability * 100).toFixed(0)}%</span>
              <span>Timeframe: {forecast.timeframe}</span>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
