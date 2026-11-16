export interface ActivityData {
  id: 'library' | 'grocery' | 'appointment' | 'community'
  title: string
  icon: string
  shortDesc: string
  decisionPointsBefore: number
  decisionPointsAfter: number
  predictable: string[]
  possibleChanges: string[]
  landmarkCue: {
    title: string
    desc: string
  }
  quietPeriod: {
    time: string
    desc: string
  }
  shadeRest: {
    title: string
    desc: string
  }
}

export const ACTIVITIES: ActivityData[] = [
  {
    id: 'library',
    title: 'Library visit',
    icon: '📚',
    shortDesc: 'Entrance, landmark and quieter period.',
    decisionPointsBefore: 3,
    decisionPointsAfter: 2,
    predictable: [
      'Automatic glass sliding doors at the main entrance',
      'Consistent non-slip flooring throughout the ground floor',
      'Information and help desk staffed directly opposite the entry',
      'Book return chute clearly labelled with high-contrast text'
    ],
    possibleChanges: [
      'Seasonal display stands rearranged near the reading lounge',
      'Staff shift changes at the desk around midday',
      'Occasional children’s storytime session in the rear corner',
      'Digital return kiosk may have a short line during peak hours'
    ],
    landmarkCue: {
      title: 'Red brick building',
      desc: 'A stable, recognisable cue at a decision point.'
    },
    quietPeriod: {
      time: '10:00–11:00 AM',
      desc: 'From daytime sensory schedule (9am–5pm window only).'
    },
    shadeRest: {
      title: '80% shade • 3 rest points',
      desc: 'Comfort context without a complex GIS dashboard.'
    }
  },
  {
    id: 'grocery',
    title: 'Grocery shopping',
    icon: '🛒',
    shortDesc: 'Familiar zones and unexpected changes.',
    decisionPointsBefore: 4,
    decisionPointsAfter: 2,
    predictable: [
      'Fresh produce section immediately upon entering the market',
      'Wide central entrance corridor with baskets on the left',
      'Staffed checkout registers remain in permanent fixed bays',
      'High-contrast overhead aisle numbers with large clear lettering'
    ],
    possibleChanges: [
      'Promotional endcap displays updated weekly',
      'Floor restocking cartons in middle aisles between 1:00 PM and 2:30 PM',
      'Refrigeration fans cycling on with humming sounds',
      'Checkout queues longer between 12:00 PM and 1:30 PM'
    ],
    landmarkCue: {
      title: 'Green pharmacy cross',
      desc: 'High-contrast visual beacon visible across the shopping plaza.'
    },
    quietPeriod: {
      time: '9:30–10:30 AM',
      desc: 'Dimmed supermarket background music and low foot traffic.'
    },
    shadeRest: {
      title: '70% canopy shade • 2 rest benches',
      desc: 'Covered plaza walkway from car park to entrance with seating.'
    }
  },
  {
    id: 'appointment',
    title: 'Appointment',
    icon: '📅',
    shortDesc: 'Entry, sequence and waiting area.',
    decisionPointsBefore: 4,
    decisionPointsAfter: 1,
    predictable: [
      'Reception counter directly facing the sliding door entrance',
      'Quiet waiting lounge equipped with firm armchairs and matte walls',
      'Practitioner or nurse calls your name directly from the seating area',
      'Accessible restroom clearly marked right beside the waiting bay'
    ],
    possibleChanges: [
      'Doctor running 10–15 minutes behind schedule on busy mornings',
      'Different receptionist on duty compared to your last visit',
      'Waiting area TV volume variations depending on broadcast',
      'Short queue at reception desk upon initial arrival'
    ],
    landmarkCue: {
      title: 'Blue clinic awning & bronze bell',
      desc: 'Distinctive exterior architectural cue before entering the lobby.'
    },
    quietPeriod: {
      time: '11:00 AM–12:00 PM',
      desc: 'Post-morning appointment lull with minimal clinic lobby wait.'
    },
    shadeRest: {
      title: '90% covered walkway • 4 seating nooks',
      desc: 'Fully sheltered transition path from public transport stop.'
    }
  },
  {
    id: 'community',
    title: 'Community centre',
    icon: '🏡',
    shortDesc: 'Entry, room identification and cues.',
    decisionPointsBefore: 3,
    decisionPointsAfter: 1,
    predictable: [
      'Large double doors with low-glare brass push handles',
      'Central foyer bulletin board displaying the daily schedule card',
      'Courtyard garden accessible through side French doors',
      'Hot tea and water refreshment station in the communal hall'
    ],
    possibleChanges: [
      'Art workshop tables temporarily arranged in the main foyer',
      'Gentle exercise music audible from the adjoining studio',
      'Front visitor parking spaces occupied during morning club hours',
      'Temporary event signs placed along the reception hallway'
    ],
    landmarkCue: {
      title: 'Heritage oak tree & stone bench',
      desc: 'Prominent, timeless natural cue right beside the main front pathway.'
    },
    quietPeriod: {
      time: '1:30–2:30 PM',
      desc: 'Quiet inter-session period between morning and afternoon groups.'
    },
    shadeRest: {
      title: '85% natural canopy • 5 park benches',
      desc: 'Tree-lined paved pathway with resting spots every 20 metres.'
    }
  }
]

export interface DestinationAnchor {
  id: string
  name: string
  icon: string
  address: string
  category: string
  essentials: string
  shadeTip: string
}

export const COLD_START_ANCHORS: DestinationAnchor[] = [
  {
    id: 'library',
    name: 'Frankston Library (Playne St)',
    icon: '📚',
    address: '60 Playne St, Frankston VIC 3199',
    category: 'library',
    essentials: 'Library card, reading glasses, reusable water bottle, return items.',
    shadeTip: 'Quiet indoor reading corners and shaded outdoor civic courtyard seating.'
  },
  {
    id: 'supermarket',
    name: 'Bayside Centre (Beach St Entrance)',
    icon: '🛒',
    address: '28 Beach St, Frankston VIC 3199',
    category: 'supermarket',
    essentials: 'Sturdy shopping bag, written shopping list, payment card, companion phone number.',
    shadeTip: 'Air-conditioned mall benches near centre court; quieter near South street entrance.'
  },
  {
    id: 'pharmacy',
    name: 'Chemist Warehouse (Wells St)',
    icon: '💊',
    address: '49 Wells St, Frankston VIC 3199',
    category: 'pharmacy',
    essentials: 'Prescription scripts, Medicare card, concession card, bottle of water.',
    shadeTip: 'Seated waiting area inside dispensary; sheltered awning along street frontage.'
  },
  {
    id: 'doctor',
    name: 'Frankston Medical Clinic (Beach St)',
    icon: '🩺',
    address: '111 Beach St, Frankston VIC 3199',
    category: 'doctor',
    essentials: 'Appointment card, medication list, Medicare card, reading glasses.',
    shadeTip: 'Spacious waiting room chairs; ramped entrance with covered vehicle drop-off.'
  },
  {
    id: 'park',
    name: 'Beauty Park (Spring St Entrance)',
    icon: '🌳',
    address: 'Spring St, Frankston VIC 3199',
    category: 'park',
    essentials: 'Comfortable walking shoes, sun hat, sunglasses, reusable water bottle.',
    shadeTip: 'Mature tree canopy benches and sheltered lakeside pavilion.'
  }
]
