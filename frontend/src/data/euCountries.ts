export type EuCountry = {
  name: string
  officialLanguages: string[]
  defaultLanguage: string
}

export const euCountries: EuCountry[] = [
  {
    name: 'Austria',
    officialLanguages: ['German'],
    defaultLanguage: 'German',
  },
  {
    name: 'Belgium',
    officialLanguages: ['Dutch', 'French', 'German'],
    defaultLanguage: 'Dutch',
  },
  {
    name: 'Bulgaria',
    officialLanguages: ['Bulgarian'],
    defaultLanguage: 'Bulgarian',
  },
  {
    name: 'Croatia',
    officialLanguages: ['Croatian'],
    defaultLanguage: 'Croatian',
  },
  {
    name: 'Cyprus',
    officialLanguages: ['Greek', 'Turkish'],
    defaultLanguage: 'Greek',
  },
  {
    name: 'Czechia',
    officialLanguages: ['Czech'],
    defaultLanguage: 'Czech',
  },
  {
    name: 'Denmark',
    officialLanguages: ['Danish'],
    defaultLanguage: 'Danish',
  },
  {
    name: 'Estonia',
    officialLanguages: ['Estonian'],
    defaultLanguage: 'Estonian',
  },
  {
    name: 'Finland',
    officialLanguages: ['Finnish', 'Swedish'],
    defaultLanguage: 'Finnish',
  },
  {
    name: 'France',
    officialLanguages: ['French'],
    defaultLanguage: 'French',
  },
  {
    name: 'Germany',
    officialLanguages: ['German'],
    defaultLanguage: 'German',
  },
  {
    name: 'Greece',
    officialLanguages: ['Greek'],
    defaultLanguage: 'Greek',
  },
  {
    name: 'Hungary',
    officialLanguages: ['Hungarian'],
    defaultLanguage: 'Hungarian',
  },
  {
    name: 'Ireland',
    officialLanguages: ['Irish', 'English'],
    defaultLanguage: 'Irish',
  },
  {
    name: 'Italy',
    officialLanguages: ['Italian'],
    defaultLanguage: 'Italian',
  },
  {
    name: 'Latvia',
    officialLanguages: ['Latvian'],
    defaultLanguage: 'Latvian',
  },
  {
    name: 'Lithuania',
    officialLanguages: ['Lithuanian'],
    defaultLanguage: 'Lithuanian',
  },
  {
    name: 'Luxembourg',
    officialLanguages: ['Luxembourgish', 'French', 'German'],
    defaultLanguage: 'Luxembourgish',
  },
  {
    name: 'Malta',
    officialLanguages: ['Maltese', 'English'],
    defaultLanguage: 'Maltese',
  },
  {
    name: 'Netherlands',
    officialLanguages: ['Dutch'],
    defaultLanguage: 'Dutch',
  },
  {
    name: 'Poland',
    officialLanguages: ['Polish'],
    defaultLanguage: 'Polish',
  },
  {
    name: 'Portugal',
    officialLanguages: ['Portuguese'],
    defaultLanguage: 'Portuguese',
  },
  {
    name: 'Romania',
    officialLanguages: ['Romanian'],
    defaultLanguage: 'Romanian',
  },
  {
    name: 'Slovakia',
    officialLanguages: ['Slovak'],
    defaultLanguage: 'Slovak',
  },
  {
    name: 'Slovenia',
    officialLanguages: ['Slovenian'],
    defaultLanguage: 'Slovenian',
  },
  {
    name: 'Spain',
    officialLanguages: ['Spanish'],
    defaultLanguage: 'Spanish',
  },
  {
    name: 'Sweden',
    officialLanguages: ['Swedish'],
    defaultLanguage: 'Swedish',
  },
]

export const availableLanguages = Array.from(
  new Set(euCountries.flatMap((country) => country.officialLanguages)),
).sort((left, right) => left.localeCompare(right))
