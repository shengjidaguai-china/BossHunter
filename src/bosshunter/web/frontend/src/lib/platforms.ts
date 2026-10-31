export const PLATFORM_LABELS: Record<string, string> = {
  boss: 'BOSS 直聘',
  zhilian: '智联招聘',
  '51job': '前程无忧',
  liepin: '猎聘',
}

export const PLATFORM_SHORT_LABELS: Record<string, string> = {
  boss: 'BOSS',
  zhilian: '智联',
  '51job': '51job',
  liepin: '猎聘',
}

export const DELIVERY_ONLY_PLATFORMS = ['zhilian', '51job', 'liepin'] as const

export const PLATFORM_DELIVERY_NOTICE = '智联按指定的 PDF 自动选择简历并投递；51job、猎聘使用网站默认简历。未指定简历、文件不匹配、问卷、验证码或无法核实结果时停止，需人工处理。不支持监测、自动聊天或额外简历发送；全流程仍仅支持 BOSS。'
export const PLATFORM_SAFETY_NOTICE = '复用全局发送时间窗口、发送间隔和每日总额度，共享风控冷却与持久暂停；不自动绕过验证码，不能保证防封号。'

export function deliveryConfirmation(count: number) {
  return `确认投递已选择的 ${count} 个岗位吗？支持 BOSS、智联、51job、猎聘。\n${PLATFORM_DELIVERY_NOTICE}\n${PLATFORM_SAFETY_NOTICE}`
}

export const PLATFORM_SAFETY_FIELDS = [
  { key: 'daily_search_page_limit', label: '单日搜索页上限', defaultValue: 20 },
  { key: 'daily_detail_page_limit', label: '单日详情页上限', defaultValue: 50 },
  { key: 'daily_platform_page_limit', label: '单日页面访问总上限', defaultValue: 80 },
  { key: 'daily_delivery_limit', label: '单日投递上限', defaultValue: 10 },
] as const

export function platformSafetyError(config: Record<string, any>): string | null {
  for (const platform of DELIVERY_ONLY_PLATFORMS) {
    for (const field of PLATFORM_SAFETY_FIELDS) {
      const value = config.platforms?.[platform]?.safety?.[field.key]
      if (value !== undefined && (!Number.isSafeInteger(value) || value <= 0)) {
        return `${PLATFORM_LABELS[platform]}${field.label}必须为正整数`
      }
    }
  }
  return null
}

export function withPlatformSafetyDefaults(config: Record<string, any>) {
  const platforms = { ...config.platforms }
  for (const platform of DELIVERY_ONLY_PLATFORMS) {
    const current = platforms[platform] || {}
    platforms[platform] = {
      ...current,
      safety: {
        ...Object.fromEntries(PLATFORM_SAFETY_FIELDS.map(field => [field.key, field.defaultValue])),
        ...current.safety,
      },
    }
  }
  return { ...config, platforms }
}


export function platformDeliveryPauseLabel(reason?: string): string | undefined {
  const labels: Record<string, string> = {
    resume_selection_required: '平台要求选择或完善投递简历。请打开原平台页面处理；本任务已暂停，不会自动再次点击。',
    apply_button_obscured: '投递按钮被弹窗遮挡或不在可点击区域。请打开原平台页面处理简历选择等弹窗，并先核对投递状态，避免重复投递。',
    questionnaire_required: '平台要求补充申请信息或填写问卷，请在原平台页面处理。',
    dialog_requires_review: '平台出现需要人工确认的弹窗，请打开原平台页面检查。',
    delivery_attempt_requires_review: '此前已尝试申请，结果尚待核对。请先在原平台确认投递状态，系统不会重复提交。',
    delivery_result_unknown: '已经尝试申请，但未取得明确成功回执。请先在原平台核对结果，系统不会重复提交。',
    already_applied: '平台显示该岗位已经申请，请核对原平台记录；本次未重复投递。',
    captcha: '平台要求验证码或安全验证，任务已暂停并进入冷却，请在原平台人工处理。',
    rate_limit: '平台提示访问或操作频繁，任务已暂停并进入冷却。',
    blocked: '平台出现访问限制，任务已暂停并进入冷却。',
    login_required: '招聘平台要求重新登录，请在原平台页面完成登录。',
    paid_recommendation: '页面出现付费或推广提示，请在原平台人工检查。',
    apply_button_ambiguous: '未找到唯一可用的投递按钮，页面结构可能已变化；本次没有自动点击。',
    apply_button_disabled: '投递按钮暂不可用，请在原平台检查岗位和简历状态。',
    apply_link_requires_review: '投递入口需要跳转其他页面，请在原平台人工处理。',
    job_identity_mismatch: '详情页与选中的岗位信息不一致，本次没有自动点击。',
    detail_root_ambiguous: '无法可靠识别职位详情区域，页面可能未加载完成或结构已变化；本次没有自动点击。',
    page_not_stable: '职位页面尚未稳定加载，本次已暂停。',
    page_unreadable: '无法读取平台页面；请先核对投递状态，再处理页面连接问题。',
    open_page_failed: '无法打开职位详情页，本次没有投递。',
    delivery_confirmation_required: '该岗位需要重新经过人工确认后才能投递。',
    job_identity_changed: '岗位信息在确认后发生了变化，本次已暂停。',
    daily_delivery_limit: '该平台今日投递额度已用完，未处理岗位已保留。',
    daily_platform_page_limit: '该平台今日页面访问额度已用完，未处理岗位已保留。',
    persistent_risk_lock: '平台仍处于安全冷却，任务已暂停。',
    unsupported_delivery_platform: '当前来源平台没有可用的投递适配器。',
  }
  return reason ? labels[reason] : undefined
}
