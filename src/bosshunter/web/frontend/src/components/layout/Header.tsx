import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { Activity, Smartphone, X, Copy, Check } from 'lucide-react'

const pageTitles: Record<string, string> = {
  '/': '工作台',
  '/jobs': '岗位池',
  '/monitor': '监测执行',
  '/config': '配置',
}

export function Header() {
  const location = useLocation()
  const title = pageTitles[location.pathname] || 'BossHunter'
  const [showMobileModal, setShowMobileModal] = useState(false)
  const [mobileInfo, setMobileInfo] = useState<{ mobile_url: string; primary_ip: string } | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (showMobileModal && !mobileInfo) {
      fetch('/api/mobile/info')
        .then(r => r.json())
        .then(data => setMobileInfo(data))
        .catch(() => {})
    }
  }, [showMobileModal, mobileInfo])

  const copyUrl = () => {
    if (mobileInfo?.mobile_url) {
      navigator.clipboard.writeText(mobileInfo.mobile_url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <>
      <header className="h-14 md:h-16 border-b border-card-border bg-[#FFFCFA] flex items-center justify-between px-4 md:px-6 shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="flex md:hidden w-7 h-7 rounded-xl bg-primary text-white items-center justify-center shadow-sm">
            <span className="font-black text-xs">BH</span>
          </div>
          <h1 className="text-base md:text-lg font-black text-foreground">{title}</h1>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setShowMobileModal(true)}
            className="hidden sm:inline-flex items-center gap-1.5 rounded-xl border border-card-border bg-white px-2.5 py-1.5 text-xs font-bold text-foreground transition-colors hover:border-primary hover:text-primary shadow-sm"
          >
            <Smartphone className="w-3.5 h-3.5 text-primary" />
            <span>手机端连接</span>
          </button>
          <div className="flex items-center gap-1.5 md:gap-2 text-xs text-muted">
            <Activity className="w-3 h-3 text-success animate-pulse" />
            <span className="hidden sm:inline">本地服务运行中</span>
            <span className="sm:hidden text-[11px] font-bold text-success">已连接</span>
          </div>
        </div>
      </header>

      {/* 手机扫码弹窗 */}
      {showMobileModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4 animate-in fade-in">
          <div className="w-full max-w-sm rounded-3xl border border-card-border bg-white p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-xl bg-[#FFF0E5] text-primary flex items-center justify-center">
                  <Smartphone className="w-4 h-4" />
                </div>
                <h3 className="font-black text-base text-foreground">手机端扫码连接</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowMobileModal(false)}
                className="rounded-xl p-1.5 text-muted hover:bg-[#FFFCFA] hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="text-center space-y-3">
              <div className="inline-block rounded-2xl border border-card-border p-3 bg-white shadow-inner">
                <img
                  src="/api/mobile/qrcode"
                  alt="手机扫码二维码"
                  className="w-48 h-48 mx-auto"
                />
              </div>
              <p className="text-xs text-muted leading-5">
                请确保手机与电脑连入<span className="font-bold text-foreground">同一 Wi-Fi</span>，打开微信或系统相机直接扫码。
              </p>
            </div>

            {mobileInfo && (
              <div className="flex items-center justify-between gap-2 rounded-2xl border border-card-border bg-[#FFFCFA] px-3 py-2 text-xs">
                <span className="font-mono text-muted truncate">{mobileInfo.mobile_url}</span>
                <button
                  type="button"
                  onClick={copyUrl}
                  className="flex items-center gap-1 font-bold text-primary shrink-0 hover:underline"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-success" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? '已复制' : '复制'}</span>
                </button>
              </div>
            )}

            <div className="text-[11px] text-muted space-y-1 bg-[#FFF0E5]/50 p-3 rounded-2xl">
              <div className="font-bold text-primary">💡 提示:</div>
              <div>• 手机浏览器打开后，选择「添加到主屏幕」即可全屏秒开。</div>
              <div>• 若手机打不开，请检查电脑防火墙是否放行了 8686 端口。</div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
