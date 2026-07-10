// ============================================================
// Synthetic demo clients (ALL FICTIONAL — no real customer data)
// ============================================================
// Four scripted personas, each exercising a different AML/KYC branch:
//   - 陳大文   : PEP (former foreign vice-minister), income/turnover mismatch
//   - 李美玲   : address proof expired (> 3 months)
//   - 王志強   : suspicious source of funds (large single deposit vs income)
//   - 張正常   : clean, materials complete (control case)
//
// Two-layer structure mirrors the Trader Admin System API:
//   account  — AccMast fields (trading system account record)
//   kyc      — compliance layer (AML/KYC due-diligence fields)
//
// Used by: IntakePanel (onboarding screening), DemoWorkbench (regulatory
// impact), TransactionMonitor (transaction behavior templates).
// ============================================================

export interface ClientMeta {
  id: string
  nameZh: string
  nameEn: string
  tag: string
  hint: string
  businessType: string
}

export interface ClientData {
  account: Record<string, unknown>
  kyc: Record<string, unknown>
  [key: string]: unknown
}

// --- Metadata shown on the picker cards ------------------------------------
export const DEMO_CLIENT_METAS: ClientMeta[] = [
  {
    id: 'SPDEMO001',
    nameZh: '陳大文',
    nameEn: 'CHAN Tai Man',
    tag: 'PEP 政治人物',
    hint: '曾任外国副部长，年收入 80 万却预期月交易 800 万',
    businessType: '保证金证券账户',
  },
  {
    id: 'SPDEMO002',
    nameZh: '李美玲',
    nameEn: 'LEE Mei Ling',
    tag: '地址證明超期',
    hint: '银行月结单签发于 2026-01-15，已超出三个月有效期',
    businessType: '现金证券账户',
  },
  {
    id: 'SPDEMO003',
    nameZh: '王志強',
    nameEn: 'WONG Chi Keung',
    tag: '資金來源可疑',
    hint: '自由职业、年收入 30 万，却单笔入金 500 万',
    businessType: '保证金证券账户',
  },
  {
    id: 'SPDEMO004',
    nameZh: '張正常',
    nameEn: 'CHEUNG Normal',
    tag: '資料齊全',
    hint: '在职软件工程师，收入与交易规模相符，材料齐全',
    businessType: '现金证券账户',
  },
]

// --- Per-client AccMast + KYC layers ---------------------------------------
const CLIENTS: Record<string, ClientData> = {
  SPDEMO001: {
    account: {
      accNo: 'SPDEMO001',
      accName: '陳大文',
      accNameUtf: '陈大文',
      idNo: 'A123456(8)',
      idType: 'HKID',
      baseCcy: 'HKD',
      aeId: 'AE001',
      maddress1: '香港中環德輔道中123號',
      maddress2: '盛富大廈18樓1801室',
      mobilePhone: '+852-9876-5432',
      email: 'cmchan.demo@example.com',
      country: 'HK',
      sex: 'M',
      accType: 'MARGIN',
      openAccountDate: '20260708',
    },
    kyc: {
      nationality: 'HK',
      date_of_birth: '1965-03-15',
      occupation: '前政府官員（已退休）',
      employer: '（已退休）',
      annual_income: 800000,
      net_worth: 5000000,
      source_of_funds: '投資收益',
      pep_flag: true,
      pep_details: '2018-2022 年間曾任某國財政部副部長',
      risk_rating: 'high',
      address_proof_date: '2026-05-10',
      address_proof_type: '水電費賬單',
      expected_monthly_turnover: 8000000,
      tax_residency: 'HK',
      hk_tax_id: 'A123456(8)',
    },
  },
  SPDEMO002: {
    account: {
      accNo: 'SPDEMO002',
      accName: '李美玲',
      accNameUtf: '李美玲',
      idNo: 'B765432(1)',
      idType: 'HKID',
      baseCcy: 'HKD',
      aeId: 'AE002',
      maddress1: '香港九龍尖沙咀彌敦道456號',
      maddress2: '半島大廈12樓1205室',
      mobilePhone: '+852-9123-4567',
      email: 'mllee.demo@example.com',
      country: 'HK',
      sex: 'F',
      accType: 'CASH',
      openAccountDate: '20260709',
    },
    kyc: {
      nationality: 'HK',
      date_of_birth: '1978-08-22',
      occupation: '中學教師',
      employer: '某資助中學',
      annual_income: 720000,
      net_worth: 3200000,
      source_of_funds: '工資收入',
      pep_flag: false,
      pep_details: '',
      risk_rating: 'medium',
      address_proof_date: '2026-01-15', // ← > 3 months old as of demo date → fail
      address_proof_type: '銀行月結單',
      expected_monthly_turnover: 150000,
      tax_residency: 'HK',
      hk_tax_id: 'B765432(1)',
    },
  },
  SPDEMO003: {
    account: {
      accNo: 'SPDEMO003',
      accName: '王志強',
      accNameUtf: '王志强',
      idNo: 'C135790(2)',
      idType: 'HKID',
      baseCcy: 'HKD',
      aeId: 'AE001',
      maddress1: '香港新界沙田沙田正街11號',
      maddress2: '沙田中心12樓12室',
      mobilePhone: '+852-9234-5678',
      email: 'ckwong.demo@example.com',
      country: 'HK',
      sex: 'M',
      accType: 'MARGIN',
      openAccountDate: '20260707',
    },
    kyc: {
      nationality: 'HK',
      date_of_birth: '1985-11-30',
      occupation: '自由職業（網絡設計）',
      employer: '自僱',
      annual_income: 300000,
      net_worth: 1500000,
      source_of_funds: '積蓄',
      pep_flag: false,
      pep_details: '',
      risk_rating: 'medium',
      address_proof_date: '2026-06-20',
      address_proof_type: '水電費賬單',
      expected_monthly_turnover: 5000000, // ← way above income → suspicious
      tax_residency: 'HK',
      hk_tax_id: 'C135790(2)',
    },
  },
  SPDEMO004: {
    account: {
      accNo: 'SPDEMO004',
      accName: '張正常',
      accNameUtf: '张正常',
      idNo: 'D246810(3)',
      idType: 'HKID',
      baseCcy: 'HKD',
      aeId: 'AE002',
      maddress1: '香港香港鰂魚涌英皇道789號',
      maddress2: '康怡花園8座18樓D室',
      mobilePhone: '+852-9345-6789',
      email: 'ncheung.demo@example.com',
      country: 'HK',
      sex: 'M',
      accType: 'CASH',
      openAccountDate: '20260709',
    },
    kyc: {
      nationality: 'HK',
      date_of_birth: '1990-05-12',
      occupation: '軟件工程師',
      employer: '某科技公司',
      annual_income: 960000,
      net_worth: 4800000,
      source_of_funds: '工資收入',
      pep_flag: false,
      pep_details: '',
      risk_rating: 'low',
      address_proof_date: '2026-06-25',
      address_proof_type: '水電費賬單',
      expected_monthly_turnover: 300000, // ← consistent with income → clean
      tax_residency: 'HK',
      hk_tax_id: 'D246810(3)',
    },
  },
}

export function getClientMeta(id: string): ClientMeta | null {
  return DEMO_CLIENT_METAS.find((c) => c.id === id) ?? null
}

export function getClientData(id: string): ClientData | null {
  return CLIENTS[id] ?? null
}

// Flat array (account+kyc merged) for the regulatory impact analysis, which
// sends all clients to the backend in one batch.
export const DEMO_CLIENTS: Record<string, unknown>[] = DEMO_CLIENT_METAS.map(
  (m) => ({
    id: m.id,
    nameZh: m.nameZh,
    nameEn: m.nameEn,
    businessType: m.businessType,
    ...CLIENTS[m.id].account,
    ...CLIENTS[m.id].kyc,
  }),
)
