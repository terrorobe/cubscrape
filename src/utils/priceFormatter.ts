/**
 * Price formatting utilities for converting cents to display strings
 */

export type Currency = 'eur' | 'usd'

export interface PriceData {
  price_eur?: number
  price_usd?: number
  original_price_eur?: number
  original_price_usd?: number
  discount_percent?: number
  is_free: boolean
  is_on_sale: boolean
}

export interface FormattedPrice {
  current: string | null
  original: string | null
  hasDiscount: boolean
  discountPercent: number
}

/**
 * Format a price in cents to a display string
 * @param priceCents Price in cents (e.g., 2499 for €24.99)
 * @param currency Currency to format as
 * @returns Formatted price string or null for free/unavailable
 */
export function formatPrice(
  priceCents: number | null | undefined,
  currency: Currency,
): string | null {
  if (priceCents === null || priceCents === undefined || priceCents === 0) {
    return null
  }

  const priceValue = priceCents / 100
  const formatted = priceValue.toFixed(2)

  switch (currency) {
    case 'eur':
      return `€${formatted}`
    case 'usd':
      return `$${formatted}`
    default:
      return `${formatted}`
  }
}

/**
 * Get the appropriate price for the given currency preference
 * @param priceData Game price data
 * @param currency Preferred currency
 * @returns Formatted price with discount information
 */
export function getPrice(
  priceData: PriceData,
  currency: Currency,
): FormattedPrice {
  const priceCents =
    currency === 'usd' ? priceData.price_usd : priceData.price_eur
  const originalPriceCents =
    currency === 'usd'
      ? priceData.original_price_usd
      : priceData.original_price_eur

  // Handle explicitly free games
  if (priceData.is_free) {
    return {
      current: 'Free',
      original: null,
      hasDiscount: false,
      discountPercent: 0,
    }
  }

  // Handle games with no pricing information (unreleased games)
  if (priceCents === undefined || priceCents === null) {
    return {
      current: null, // No price display for unreleased games
      original: null,
      hasDiscount: false,
      discountPercent: 0,
    }
  }

  // Handle zero-priced games (should be rare, but treat as free)
  if (priceCents === 0) {
    return {
      current: 'Free',
      original: null,
      hasDiscount: false,
      discountPercent: 0,
    }
  }

  const currentPrice = formatPrice(priceCents, currency)
  const originalPrice = originalPriceCents
    ? formatPrice(originalPriceCents, currency)
    : null

  return {
    current: currentPrice,
    original: originalPrice,
    hasDiscount: priceData.is_on_sale && originalPrice !== null,
    discountPercent: priceData.discount_percent ?? 0,
  }
}

/**
 * Get the best available price, falling back to other currency if preferred is unavailable
 * @param priceData Game price data
 * @param preferredCurrency Preferred currency
 * @returns Formatted price with fallback and currency info
 */
export function getBestPrice(
  priceData: PriceData,
  preferredCurrency: Currency,
): FormattedPrice & { currency: Currency } {
  const preferredResult = getPrice(priceData, preferredCurrency)

  // If preferred currency has a price, use it
  if (preferredResult.current && preferredResult.current !== 'Free') {
    return { ...preferredResult, currency: preferredCurrency }
  }

  // Fall back to other currency
  const fallbackCurrency: Currency = preferredCurrency === 'eur' ? 'usd' : 'eur'
  const fallbackResult = getPrice(priceData, fallbackCurrency)

  return { ...fallbackResult, currency: fallbackCurrency }
}

/**
 * Format a price for display in filters or sorting (numeric value)
 * @param priceData Game price data
 * @param currency Currency preference
 * @returns Numeric price value for comparisons, 0 for free games, null for unreleased games
 */
export function getPriceValue(
  priceData: PriceData,
  currency: Currency,
): number | null {
  if (priceData.is_free) {
    return 0
  }

  const priceCents =
    currency === 'usd' ? priceData.price_usd : priceData.price_eur

  if (priceCents === null || priceCents === undefined) {
    // Fall back to other currency
    const fallbackCents =
      currency === 'usd' ? priceData.price_eur : priceData.price_usd
    if (fallbackCents !== null && fallbackCents !== undefined) {
      return fallbackCents / 100
    }
    // Return null for unreleased games - safer than magic numbers
    // Filtering logic must handle null explicitly
    return null
  }

  return priceCents / 100
}
