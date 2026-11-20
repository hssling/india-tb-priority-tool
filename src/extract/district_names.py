"""Explicit district-name crosswalks for the district modules (analysis plan §9).

ITR2019: the district rows of ITR 2019 Annexure 1.13 (data year 2018), by printed State
(the State crosswalk's canonical printed name, not coarsened), in printed order. The
names are as printed, with a line-wrap hyphen removed: a hyphen at the end of a wrapped
line followed by a lower-case letter joins the word ("Chamara- janagar" ->
"Chamarajanagar"); followed by a capital it is kept ("Aurangabad- MH" ->
"Aurangabad-MH"). Every such join is listed in ITR2019_WRAPPED. Spellings are not
corrected ("Nanded Waghela MC", "Centeral Chennai") and districts are not linked to
later names (plan §9.1).

AU802: the district entries of Lok Sabha Unstarred Question 802 (7 February 2025), by
State, as printed (distinct names; Madhya Pradesh prints "Vidisha" twice, plan §9.2).

A name not listed raises KeyError naming the string and its State.
"""
from __future__ import annotations

import re

ITR2019: dict[str, tuple[str, ...]] = {
    'Andaman and Nicobar Islands': (
        'Nicobars', 'North & Middle Andaman', 'South Andaman',
    ),
    'Andhra Pradesh': (
        'Anantapur', 'Chittoor', 'Cuddapah', 'East Godavari', 'Guntur', 'Krishna',
        'Kurnool', 'Nellore', 'Prakasam', 'Srikakulam', 'Visakhapatnam', 'Vizianagaram',
        'West Godavari',
    ),
    'Arunachal Pradesh': (
        'Changlang', 'Dibang Valley', 'East Kameng', 'East Siang', 'KurungKumey', 'Lohit',
        'Lower Subansiri', 'Papumpare', 'Tawang', 'Tirap', 'Upper Siang',
        'Upper Subansiri', 'West Kameng', 'West Siang',
    ),
    'Assam': (
        'Baksa', 'Barpeta', 'Bongaigaon', 'Cachar', 'Chirang', 'Darrang', 'Dhemaji',
        'Dhubri', 'Dibrugarh', 'Goalpara', 'Golaghat', 'Hailakandi', 'Jorhat', 'Kamrup',
        'Kamrup Metro', 'KarbiAnglong', 'Karimganj', 'Kokrajhar', 'Lakhimpur', 'Marigaon',
        'Nagaon', 'Nalbari', 'North Cachar Hills', 'Sibsagar', 'Sonitpur', 'Tinsukia',
        'Udalguri',
    ),
    'Bihar': (
        'Araria', 'Arwal', 'Aurangabad-BI', 'Banka', 'Begusarai', 'Bhagalpur', 'Bhojpur',
        'Buxar', 'Darbhanga', 'Gaya', 'Gopalganj', 'Jamui', 'Jehanabad', 'Kaimur',
        'Katihar', 'Khagaria', 'Kishanganj', 'Lakhisarai', 'Madhepura', 'Madhubani',
        'Munger', 'Muzaffarpur', 'Nalanda', 'Nawada', 'PashchimChamparan', 'Patna',
        'PurbaChamparan', 'Purnia', 'Rohtas', 'Saharsa', 'Samastipur', 'Saran',
        'Sheikhpura', 'Sheohar', 'Sitamarhi', 'Siwan', 'Supaul', 'Vaishali',
    ),
    'Chandigarh': (
        'Chandigarh',
    ),
    'Chhattisgarh': (
        'Balarampur', 'Balod', 'Baloda Bazar', 'Bastar', 'Bemetara', 'Bijapur',
        'Bilaspur-CG', 'Dhamtari', 'Durg', 'Gariyaband', 'Janjgir', 'Jashpur',
        'Kabirdham (Kawardha)', 'Kondagaon', 'Korba', 'Koriya', 'Mahasamund', 'Mungeli',
        'Narayanpur', 'Raigarh-CG', 'Raipur', 'Rajnandgaon', 'Sarguja',
        'South BastarDantewada', 'Sukma', 'Surajpur', 'Uttar BastarKanker',
    ),
    'Dadra and Nagar Haveli': (
        'Dadra & Nagar Haveli',
    ),
    'Daman and Diu': (
        'Daman', 'Diu',
    ),
    'Delhi': (
        'Bijwasan', 'BJRM Chest Clinic', 'BSA Chest Clinic', 'CD Chest Clinic',
        'DDU Chest Clinic', 'GTB Chest Clinic', 'Gulabi Bagh', 'Hedgewar Chest Clinic',
        'Jhandewalan', 'Karawal Nagar', 'Kingsway', 'LN Chest Clinic', 'LRS',
        'MNCH Chest Clinic', 'Moti Nagar', 'Narela', 'NDMC', 'Nehru Nagar', 'Patparganj',
        'RK Mission', 'RTRM Chest Clinic', 'SGM Chest Clinic', 'Shahadra', 'SPM Marg',
        'SPMH Chest Clinic',
    ),
    'Goa': (
        'North Goa', 'South Goa',
    ),
    'Gujarat': (
        'Ahmadabad', 'Ahmadabad MC', 'Amreli', 'Anand', 'Arvalli', 'Banaskantha',
        'Bharuch', 'Bhavnagar', 'Botad', 'ChhotaUdepur', 'Dahod', 'Devbhumidwarka',
        'Gandhinagar', 'Gir Somnath', 'Jamnagar', 'Junagadh', 'Kachchh', 'Kheda',
        'Mahesana', 'Mahisagar', 'Morbi', 'Narmada', 'Navsari', 'Panch Mahals', 'Patan',
        'Porbandar', 'Rajkot', 'Sabarkantha', 'Surat', 'Surat Municipal Corp',
        'Surendranagar', 'The Dangs', 'Vadodara', 'Vadodara Corp', 'Valsad',
        'Vyara (Surat)',
    ),
    'Haryana': (
        'Ambala', 'Bhiwani', 'Faridabad', 'Fatehabad', 'Gurgaon', 'Hisar', 'Jhajjar',
        'Jind', 'Kaithal', 'Karnal', 'Kurukshetra', 'Mahendragarh', 'Mewat', 'Palwal',
        'Panchkula', 'Panipat', 'Rewari', 'Rohtak', 'Sirsa', 'Sonipat', 'Yamunanagar',
    ),
    'Himachal Pradesh': (
        'Bilaspur-HP', 'Chamba', 'Hamirpur-HP', 'Kangra', 'Kinnaur', 'Kullu',
        'Lahul&Spiti', 'Mandi', 'Shimla', 'Sirmaur', 'Solan', 'Una',
    ),
    'Jammu and Kashmir': (
        'Anantnag', 'Badgam', 'Baramula', 'Doda', 'Jammu', 'Kargil', 'Kathua', 'Kupwara',
        'Leh', 'Poonch', 'Pulwama', 'Rajouri', 'Srinagar', 'Udhampur',
    ),
    'Jharkhand': (
        'Bokaro', 'Chatra', 'Deoghar', 'Dhanbad', 'Dumka', 'Garhwa', 'Giridih', 'Godda',
        'Gumla', 'Hazaribagh', 'Jamtara', 'Khunti', 'Kodarma', 'Lathehar', 'Lohardaga',
        'Pakur', 'Palamu', 'PashchimiSinghbhum', 'PurbiSinghbhum', 'Ramgarh', 'Ranchi',
        'Sahibganj', 'Saraikela-Kharsawan', 'Simdega',
    ),
    'Karnataka': (
        'Bagalkot', 'Bangalore City', 'Bangalore Rural', 'Bangalore Urban', 'Belgaum',
        'Bellary', 'Bidar', 'Bijapur', 'Chamarajanagar', 'Chikkaballapur', 'Chikmagalur',
        'Chitradurga', 'Dakshina Kannada', 'Davanagere', 'Dharwad', 'Gadag', 'Gulbarga',
        'Hassan', 'Haveri', 'Kodagu', 'Kolar', 'Koppal', 'Mandya', 'Mysore', 'Raichur',
        'Ramanagara', 'Shimoga', 'Tumkur', 'Udupi', 'Uttara Kannada', 'Yadgiri',
    ),
    'Kerala': (
        'Alappuzha', 'Ernakulam', 'Idukki', 'Kannur', 'Kasaragod', 'Kollam', 'Kottayam',
        'Kozhikode', 'Malappuram', 'Palakkad', 'Pathanamthitta', 'Thiruvananthapuram',
        'Thrissur', 'Wayanad',
    ),
    'Lakshadweep': (
        'Lakshadweep',
    ),
    'Madhya Pradesh': (
        'Agar Malwa', 'Alirajpur', 'Anuppur', 'Ashoknagar', 'Balaghat', 'Barwani', 'Betul',
        'Bhind', 'Bhopal', 'Burhanpur', 'Chhatarpur', 'Chhindwara', 'Damoh', 'Datia',
        'Dewas', 'Dhar', 'Dindori', 'Guna', 'Gwalior', 'Harda', 'Hoshangabad', 'Indore',
        'Jabalpur', 'Jhabua', 'Katni', 'Khandwa', 'Khargone', 'Mandla', 'Mandsaur',
        'Morena', 'Narsinghpur', 'Neemuch', 'Panna', 'Raisen', 'Rajgarh', 'Ratlam', 'Rewa',
        'Sagar', 'Satna', 'Sehore', 'Seoni', 'Shahdol', 'Shajapur', 'Sheopur', 'Shivpuri',
        'Sidhi', 'Singrauli', 'Tikamgarh', 'Ujjain', 'Umaria', 'Vidisha',
    ),
    'Maharashtra': (
        'Ahmadnagar', 'Ahmednagar MC', 'Akola', 'Akola MC', 'Amravati', 'Amravati MC',
        'Andheri East', 'Andheri West', 'Aurangabad MC', 'Aurangabad-MH',
        'Bail Bazar Road', 'Bandra East', 'Bandra West', 'Bhandara', 'Bhiwandi Nizampur',
        'Bid', 'Borivali', 'Buldana', 'Byculla', 'Centenary', 'Chandrapur', 'Chembur',
        'Colaba', 'Dadar', 'Dahisar', 'Dhule', 'Dhule MC', 'Gadchiroli', 'Ghatkopar',
        'Gondiya', 'Goregaon', 'Govandi', 'Grant Road', 'Hingoli', 'Jalgaon', 'Jalgaon MC',
        'Jalna', 'Kalyan Dombivli MC', 'Kandivali', 'Kolhapur', 'Kolhapur MC', 'Kurla',
        'Latur', 'Malad', 'Malegaon Corporation', 'Mira Bhayander', 'Mulund', 'Nagpur',
        'Nagpur MC', 'Nanded', 'Nanded Waghela MC', 'Nandurbar', 'Nashik', 'Nashik Corp',
        'Navi Mumbai', 'Osmanabad', 'Parbhani', 'Parel', 'Pimpri Chinchwad', 'Prabhadevi',
        'Pune', 'Pune Rural', 'Raigarh-MH', 'Ratnagiri', 'Sangli', 'Sangli MC', 'Satara',
        'Sindhudurg', 'Sion', 'Solapur', 'Solapur MC', 'Thane', 'Thane MC',
        'Ulhasnagar MC', 'Vasai Virar', 'Vikhroli', 'Wardha', 'Washim', 'Yavatmal',
    ),
    'Manipur': (
        'Bishnupur', 'Chandel', 'Churachandpur', 'Imphal East', 'Imphal West', 'Senapati',
        'Tamenglong', 'Thoubal', 'Ukhrul',
    ),
    'Meghalaya': (
        'East Garo Hills', 'East Khasi Hills', 'Jaintia Hills', 'Ri Bhoi',
        'South Garo Hills', 'West Garo Hills', 'West Khasi Hills',
    ),
    'Mizoram': (
        'Aizawl', 'Champhai', 'Kolasib', 'Lawngtlai', 'Lunglei', 'Mamit', 'Saiha',
        'Serchhip',
    ),
    'Nagaland': (
        'Mon', 'Dimapur', 'Kiphire', 'Kohima', 'Longleng', 'Mokokchung', 'Peren', 'Phek',
        'Tuensang', 'Wokha', 'Zunheboto',
    ),
    'Odisha': (
        'Anugul', 'Balangir', 'Baleshwar', 'Bargarh', 'Baudh', 'Bhadrak',
        'Bhubaneshwar MC', 'Cuttack', 'Debagarh', 'Dhenkanal', 'Gajapati', 'Ganjam',
        'Jagatsinghapur', 'Jajapur', 'Jharsuguda', 'Kalahandi', 'Kandhamal', 'Kendrapara',
        'Kendujhar', 'Khordha', 'Koraput', 'Malkangiri', 'Mayurbhanj', 'Nabarangapur',
        'Nayagarh', 'Nuapada', 'Puri', 'Rayagada', 'Sambalpur', 'Sonapur', 'Sundargarh',
    ),
    'Puducherry': (
        'Puducherry',
    ),
    'Punjab': (
        'Amritsar', 'Barnala', 'Bathinda', 'Faridkot', 'Fatehgarh Sahib', 'Fazilka',
        'Firozpur', 'Gurdaspur', 'Hoshiarpur', 'Jalandhar', 'Kapurthala', 'Ludhiana',
        'Mansa-PN', 'Moga', 'Mohali', 'Muktsar', 'Nawanshahr', 'Pathankot', 'Patiala',
        'Rupnagar', 'Sangrur', 'Tarn Taran',
    ),
    'Rajasthan': (
        'Ajmer', 'Alwar', 'Banswara', 'Baran', 'Barmer', 'Bharatpur', 'Bhilwara',
        'Bikaner', 'Bundi', 'Chittaurgarh', 'Churu', 'Dausa', 'Dhaulpur', 'Dungarpur',
        'Ganganagar', 'Hanumangarh', 'Jaipur', 'Jaipur DTC II', 'Jaisalmer', 'Jalore',
        'Jhalawar', 'Jhunjhunun', 'Jodhpur', 'Karauli', 'Kota', 'Nagaur', 'Pali',
        'Pratapgarh', 'Rajsamand', 'Sawai Madhopur', 'Sikar', 'Sirohi', 'Tonk', 'Udaipur',
    ),
    'Sikkim': (
        'East District', 'North District', 'Singtam', 'South District', 'West District',
    ),
    'Tamil Nadu': (
        'Centeral Chennai', 'Coimbatore', 'Cuddalore', 'Dharmapuri', 'Dindigul', 'Erode',
        'Kancheepuram', 'Kanniyakumari', 'Karur', 'Krishnagiri', 'Madurai', 'Nagapattinam',
        'Namakkal', 'North Chennai', 'Perambalur', 'Pudukkottai', 'Ramanathapuram',
        'Salem', 'Sivaganga', 'South Chennai', 'Thanjavur', 'The Nilgiris', 'Theni',
        'Thiruvallur', 'Thiruvarur', 'Thoothukudi', 'Tiruchirappalli', 'Tirunelveli',
        'Tiruppur', 'Tiruvannamalai', 'Vellore', 'Viluppuram', 'Virudhunagar',
    ),
    'Telangana': (
        'Adilabad', 'Asifabad', 'Bhadrachalam', 'Gadwal', 'Hyderabad', 'Jagtiyal',
        'Jangaon', 'Jayashankar', 'Kamareddy', 'Karimnagar', 'Khammam', 'Mahabubabad',
        'Mahbubnagar', 'Mancherial', 'Medak', 'Medchal', 'Nagarkurnool', 'Nalgonda',
        'Nirmal', 'Nizamabad', 'Peddapally', 'Rangareddy', 'Sangareddy', 'Siddipet',
        'Sircilla', 'Suryapet', 'Vikarabad', 'Wanaparthy', 'Warangal Rural',
        'Warangal Urban', 'Yadadri',
    ),
    'Tripura': (
        'Dhalai', 'Gomati', 'Khowai', 'North Tripura', 'Sepahijala', 'South Tripura',
        'Unakoti', 'West Tripura',
    ),
    'Uttar Pradesh': (
        'Agra', 'Aligarh', 'Allahabad', 'Ambedkar Nagar', 'Amethi', 'Auraiya', 'Azamgarh',
        'Baghpat', 'Bahraich', 'Ballia', 'Balrampur', 'Banda', 'Barabanki', 'Bareilly',
        'Basti', 'Bijnor', 'Budaun', 'Bulandshahar', 'Chandauli', 'Chitrakoot', 'Deoria',
        'Etah', 'Etawah', 'Faizabad', 'Farrukhabad', 'Fatehpur', 'Firozabad',
        'Gautam Budh Nagar', 'Ghaziabad', 'Ghazipur', 'Gonda', 'Gorakhpur', 'Hamirpur-UP',
        'Hapur', 'Hardoi', 'Hathras', 'Jalaun', 'Jaunpur', 'Jhansi', 'Jyotiba Phule Nagar',
        'Kannauj', 'Kanpur Dehat', 'Kanpur Nagar', 'Kanshiram Nagar', 'Kaushambi', 'Kheri',
        'Kushinagar', 'Lalitpur', 'Lucknow', 'Maharajganj', 'Mahoba', 'Mainpuri',
        'Mathura', 'Mau', 'Meerut', 'Mirzapur', 'Moradabad', 'Muzaffarnagar', 'Pilibhit',
        'Pratapgarh', 'Rae Bareli', 'Rampur', 'Saharanpur', 'Sambhal', 'Sant Kabir Nagar',
        'Sant Ravidas Nagar', 'Shahjahanpur', 'Shamli', 'Shravasti', 'Siddharthnagar',
        'Sitapur', 'Sonbhadra', 'Sultanpur', 'Unnao', 'Varanasi',
    ),
    'Uttarakhand': (
        'Almora', 'Bageshwar', 'Chamoli', 'Champawat', 'Dehradun', 'Garhwal', 'Hardwar',
        'Nainital', 'Pithoragarh', 'Rudraprayag', 'Tehri Garhwal', 'Udhamsingh Nagar',
        'Uttarkashi',
    ),
    'West Bengal': (
        'Alipore', 'Alipurduar', 'Bagbazar', 'Bankura', 'Barddhaman', 'Basirhat', 'Behala',
        'Birbhum', 'Bishnupur', 'Dakshin Dinajpur', 'Darjiling', 'Diamond Harbour',
        'Haora', 'Hazi', 'Hugli', 'Jalpaiguri', 'Jhargram', 'Kalimpong', 'Koch Bihar',
        'Maldah', 'Maniktala', 'Manshatala', 'Medinipur East', 'Medinipur West', 'MTMTB',
        'Murshidabad', 'Nadia', 'Nandigram', 'North 24 Parganas', 'Paschim Bardhaman',
        'Puruliya', 'Rampurhat', 'South 24 Parganas', 'Strand Bank', 'Tangra',
        'Tollygunge', 'Uttar Dinajpur',
    ),
}

# (State, name as joined from the wrapped printed lines) -> name.
ITR2019_WRAPPED: dict[tuple[str, str], str] = {
    ('Bihar', 'Aurangabad- BI'): 'Aurangabad-BI',
    ('Bihar', 'PashchimCham- paran'): 'PashchimChamparan',
    ('Bihar', 'PurbaCham- paran'): 'PurbaChamparan',
    ('Chhattisgarh', 'South Bas- tarDantewa- da'): 'South BastarDantewada',
    ('Gujarat', 'Devbhumid- warka'): 'Devbhumidwarka',
    ('Jharkhand', 'PashchimiSing- hbhum'): 'PashchimiSinghbhum',
    ('Jharkhand', 'PurbiSingh- bhum'): 'PurbiSinghbhum',
    ('Jharkhand', 'Saraikela- Kharsawan'): 'Saraikela-Kharsawan',
    ('Karnataka', 'Chamara- janagar'): 'Chamarajanagar',
    ('Kerala', 'Thiruvanantha- puram'): 'Thiruvananthapuram',
    ('Maharashtra', 'Aurangabad- MH'): 'Aurangabad-MH',
    ('Tamil Nadu', 'Ramanathapu- ram'): 'Ramanathapuram',
}

AU802: dict[str, tuple[str, ...]] = {
    'Madhya Pradesh': (
        'Agar Malwa', 'Sagar', 'Alirajpur', 'Satna', 'Anuppur', 'Sehore', 'Ashoknagar',
        'Seoni', 'Balaghat', 'Shahdol', 'Barwani', 'Shajapur', 'Betul', 'Sheopur', 'Bhind',
        'Shivpuri', 'Bhopal', 'Sidhi', 'Burhanpur', 'Singrauli', 'Chhatarpur', 'Tikamgarh',
        'Chhindwara', 'Ujjain', 'Damoh', 'Umaria', 'Datia', 'Vidisha', 'Dewas', 'Dhar',
        'Dindori', 'Guna', 'Gwalior', 'Harda', 'Hoshangabad', 'Indore', 'Jabalpur',
        'Jhabua', 'Katni', 'Khandwa', 'Khargone', 'Mandla', 'Mandsaur', 'Morena',
        'Narsinghpur', 'Neemuch', 'Niwari', 'Panna', 'Raisen', 'Rajgarh', 'Ratlam', 'Rewa',
    ),
    'Maharashtra': (
        'Akola', 'Mumbai_Vikhroli', 'Akola Municipal Corporation',
        'Kalyan Dombivli Municipal Corporation', 'Amravati',
        'Navi Mumbai Municipal Corporation', 'Amravati Municipal Corporation', 'Raigad',
        'Buldana', 'Thane', 'Washim', 'Palghar', 'Yavatmal', 'Thane Municipal Corporation',
        'Chhatrapati Sambhajinagar', 'Bhiwandi Nizampur Municipal Corporation',
        'Chhatrapati Sambhajinagar Municipal Corporation',
        'Mira Bhayander Municipal Corporation', 'Hingoli',
        'Ulhasnagar Municipal Corporation', 'Jalna', 'Vasai Virar Municipal Corporation',
        'Parbhani', 'Bhandara', 'Beed', 'Chandrapur', 'Latur', 'Gadchiroli', 'Nanded',
        'Gondiya', 'Nanded Waghala Municipal Corporation', 'Nagpur', 'Dharashiv',
        'Nagpur Municipal Corporation', 'Mumbai_Andheri East', 'Wardha',
        'Mumbai_Andheri West', 'Ahilyanagar', 'Mumbai_Bandra East',
        'Ahilyanagar Municipal Corporation', 'Mumbai_Bandra West', 'Dhule',
        'Mumbai_Bail Bazar Road', 'Dhule Municipal Corporation', 'Mumbai_Byculla',
        'Jalgaon', 'Mumbai_Borivali', 'Jalgaon Municipal Corporation', 'Mumbai_Colaba',
        'Nandurbar', 'Mumbai_Chembur', 'Nashik', 'Mumbai_Centenary',
        'Nashik Municipal Corporation', 'Mumbai_Dadar', 'Malegaon Municipal Corporation',
        'Mumbai_Dahisar', 'Kolhapur', 'Mumbai_Ghatkopar', 'Kolhapur Municipal Corporation',
        'Mumbai_Goregaon', 'Ratnagiri', 'Mumbai_Grant Road', 'Sangli', 'Mumbai_Govandi',
        'Sangli Municipal Corporation', 'Mumbai_Kandivali', 'Sindhudurg', 'Mumbai_Kurla',
        'Satara', 'Mumbai_Malad', 'Pune Rural', 'Mumbai_Mulund',
        'Pune Municipal Corporation', 'Mumbai_Prabhadevi',
        'Pimpri Chinchwad Municipal Corporation', 'Mumbai_Parel', 'Solapur', 'Mumbai_Sion',
        'Solapur Municipal Corporation',
    ),
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def itr2019(state: str, printed: str) -> str:
    """The ITR 2019 A1.13 district name of `printed` in `state`; KeyError naming it."""
    raw = _norm(printed)
    if state not in ITR2019:
        raise KeyError(f"State not in the ITR 2019 district crosswalk: {state!r}")
    name = ITR2019_WRAPPED.get((state, raw), raw)
    if name not in ITR2019[state]:
        raise KeyError(f"district name not in the ITR 2019 crosswalk: {printed!r} ({state})")
    return name


def itr2019_count() -> int:
    return sum(len(v) for v in ITR2019.values())


def au802(state: str, printed: str) -> str:
    """The AU802 district name of `printed` in `state`; KeyError naming it."""
    raw = _norm(printed)
    if state not in AU802:
        raise KeyError(f"State not in the AU802 district crosswalk: {state!r}")
    if raw not in AU802[state]:
        raise KeyError(f"district name not in the AU802 crosswalk: {printed!r} ({state})")
    return raw


assert all(len(set(v)) == len(v) for v in ITR2019.values())
assert all(len(set(v)) == len(v) for v in AU802.values())
assert len(ITR2019["Madhya Pradesh"]) == 51 and len(ITR2019["Maharashtra"]) == 79
assert len(AU802["Madhya Pradesh"]) == 52 and len(AU802["Maharashtra"]) == 80
