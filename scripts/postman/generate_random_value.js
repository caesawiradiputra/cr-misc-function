
// --- Helper functions ---
function pad(num, size) {
    let s = String(num);
    while (s.length < size) s = '0' + s;
    return s;
}

function randomInt(min, max) {
    // inclusive
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randomDateBetween(startYear, endYear) {
    const start = new Date(startYear, 0, 1);
    const end = new Date(endYear, 11, 31);
    const t = start.getTime() + Math.random() * (end.getTime() - start.getTime());
    return new Date(t);
}

// --- Generate first 6 digits (province + regency/city + district) ---
function generateRandomAreaCode() {
    const province = randomInt(11, 94);   // plausible province code range
    const regency  = randomInt(1, 99);    // 01–99
    const district = randomInt(1, 99);    // 01–99
    return pad(province, 2) + pad(regency, 2) + pad(district, 2);
}

// --- Generate DOB part ---
// For female, add +40 to day in encoded part, but store normal day in readable DOB.
function generateDobParts(isFemale, fromYear = 1970, toYear = 2005) {
    const d = randomDateBetween(fromYear, toYear);
    let day = d.getDate();
    const month = d.getMonth() + 1;
    const yearFull = d.getFullYear();
    const yearShort = yearFull % 100;

    // add 40 to day for females (encoded part only)
    const encodedDay = isFemale ? day + 40 : day;
    const encodedPart = pad(encodedDay, 2) + pad(month, 2) + pad(yearShort, 2);

    // // human-readable DOB (dd-mm-yyyy)
    // const readablePart = `${pad(day, 2)}-${pad(month, 2)}-${yearFull}`;
    // human-readable DOB (yyyy-mm-dd)
    const readablePart = `${yearFull}-${pad(month, 2)}-${pad(day, 2)}`;
    return { encodedPart, readablePart };
}

// --- Generate serial (4 digits) ---
function generateSerial() {
    return pad(randomInt(0, 20), 4);
}

// --- Generate marital status and spouse ID if married ---
function generateMaritalStatus() {
    const maritalStatus = Math.random() < 0.5 ? "M" : "S";  // 50% married, 50% single
    let spouseIdNumber = "x";

    if (maritalStatus === "M") {
        // Generate random spouse ID number (same format as KTP)
        const spouseKtp = generateKTP();
        spouseIdNumber = spouseKtp.nik;
    }

    return {
        maritalStatus: maritalStatus,
        spouseIdNumber: spouseIdNumber
    };
}

// --- Generate obligor ID ---
// Format: OB + YYYYMMDD + HHmmSS + 0000 (left-padded sequence number, random 1-5)
function generateObligorId() {
    const randomDate = randomDateBetween(2020, 2025);
    
    const year = randomDate.getFullYear();
    const month = pad(randomDate.getMonth() + 1, 2);
    const day = pad(randomDate.getDate(), 2);
    const hours = pad(randomInt(0, 23), 2);
    const minutes = pad(randomInt(0, 59), 2);
    const seconds = pad(randomInt(0, 59), 2);
    const sequenceNumber = pad(randomInt(1, 5), 4);
    
    return "OB" + year + month + day + hours + minutes + seconds + sequenceNumber;
}

// --- Generate bank account number ---
// Format: numeric, 7-12 characters
function generateBankAccount() {
    const length = randomInt(7, 12);
    let account = "";
    for (let i = 0; i < length; i++) {
        account += randomInt(0, 9);
    }
    return account;
}

// --- Generate Indonesia machine number (nomor mesin) ---
// Format: alphanumeric, 10-17 characters
function generateMachineNumber() {
    const length = randomInt(10, 17);
    const chars = "0123456789ABCDEFGHJKLMNPRSTUVWXYZ"; // excluding I, O, Q to avoid confusion
    let machineNo = "";
    for (let i = 0; i < length; i++) {
        machineNo += chars.charAt(randomInt(0, chars.length - 1));
    }
    return machineNo;
}

// --- Generate Indonesia chassis number (nomor rangka) ---
// Format: alphanumeric, 10-17 characters
function generateChassisNumber() {
    const length = randomInt(10, 17);
    const chars = "0123456789ABCDEFGHJKLMNPRSTUVWXYZ"; // excluding I, O, Q to avoid confusion
    let chassisNo = "";
    for (let i = 0; i < length; i++) {
        chassisNo += chars.charAt(randomInt(0, chars.length - 1));
    }
    return chassisNo;
}

// --- Generate Indonesia BPKB number (nomor BPKB) ---
// Format: [2-digit province code][2-digit district code][4-digit year][4-digit sequence]
function generateBPKBNumber() {
    const provinceCode = pad(randomInt(10, 94), 2);  // valid province codes
    const districtCode = pad(randomInt(1, 99), 2);
    const year = pad(randomInt(2000, 2025) % 100, 2);  // last 2 digits of year
    const sequence = pad(randomInt(1, 9999), 4);
    
    return provinceCode + districtCode + year + sequence;
}

// --- Generate random area from price list enum ---
function generateRandomAreaPL() {
    const areas = [
        "BANDUNG",
        "CIREBON",
        "JABODETABEK",
        "JAWA TENGAH",
        "KARAWANG",
        "DENPASAR",
        "JAWA TIMUR",
        "MATARAM",
        "BANJARMASIN",
        "PONTIANAK",
        "SAMPIT",
        "KALBAGTIM",
        "AMBON",
        "MANADO",
        "MAKASSAR",
        "PALU",
        "BANGKA BELITUNG",
        "JAMBI",
        "LAMPUNG",
        "PADANG",
        "PALEMBANG",
        "BATAM FTZ",
        "BATAM NON FTZ",
        "BATAM",
        "MEDAN",
        "PEKANBARU",
        "TANJUNG PINANG"
    ];
    return areas[randomInt(0, areas.length - 1)];
}

// --- Generate random year (20 years before current year until current year) ---
function generateRandomYear() {
    const currentYear = new Date().getFullYear();
    const minYear = currentYear - 20;
    return randomInt(minYear, currentYear);
}

// --- Compose full KTP/NIK ---
function generateKTP(options) {
    options = options || {};
    const isFemale = options.isFemale === undefined ? (Math.random() < 0.5) : !!options.isFemale;

    const area6 = generateRandomAreaCode();
    const dob = generateDobParts(isFemale, options.fromYear || 1970, options.toYear || 2005);
    const serial = generateSerial();

    return {
        nik: area6 + dob.encodedPart + serial,
        isFemale: isFemale,
        area6: area6,
        dobEncoded: dob.encodedPart,
        dobReadable: dob.readablePart,
        serial: serial
    };
}

// --- Example usage in Postman ---
const result = generateKTP(); // random gender
const maritalInfo = generateMaritalStatus();
const obligorId = generateObligorId();
const bankAccount = generateBankAccount();
const machineNo = generateMachineNumber();
const chassisNo = generateChassisNumber();
const bpkbNo = generateBPKBNumber();
const areaPL = generateRandomAreaPL();
const year = generateRandomYear();
const random_id_number = result.nik;
const random_name = "USER_" + Math.random().toString(36).substring(2, 8).toUpperCase();
const random_gender = result.isFemale ? "F" : "M";
const random_marital_status = maritalInfo.maritalStatus;
const random_spouse_id_number = maritalInfo.spouseIdNumber;
const random_obligor_id = obligorId;
const random_bank_account = bankAccount;
const random_machine_no = machineNo;
const random_chassis_no = chassisNo;
const random_bpkb_no = bpkbNo;
const random_area_pl = areaPL;
const random_year = year;

// Save to collection variables
pm.collectionVariables.set("random_id_number", random_id_number);
pm.collectionVariables.set("random_name", random_name);
pm.collectionVariables.set("random_is_female", String(result.isFemale));
pm.collectionVariables.set("random_gender", random_gender);
pm.collectionVariables.set("random_area6", result.area6);
pm.collectionVariables.set("random_dob_part", result.dobReadable); // dd-mm-yyyy format
pm.collectionVariables.set("random_serial", result.serial);
pm.collectionVariables.set("random_marital_status", random_marital_status);
pm.collectionVariables.set("random_spouse_id_number", random_spouse_id_number);
pm.collectionVariables.set("random_obligor_id", random_obligor_id);
pm.collectionVariables.set("random_bank_account", random_bank_account);
pm.collectionVariables.set("random_machine_no", random_machine_no);
pm.collectionVariables.set("random_chassis_no", random_chassis_no);
pm.collectionVariables.set("random_bpkb_no", random_bpkb_no);
pm.collectionVariables.set("random_area_pl", random_area_pl);
pm.collectionVariables.set("random_year", random_year);

// Logging for debugging
console.log("Generated synthetic KTP/NIK:", random_id_number);
console.log("Gender (female?):", result.isFemale);
console.log("Area (first 6):", result.area6);
console.log("DOB encoded (for NIK):", result.dobEncoded);
console.log("DOB readable:", result.dobReadable);
console.log("Serial:", result.serial);
console.log("Generated name:", random_name);
console.log("Marital Status:", random_marital_status);
if (random_spouse_id_number) {
    console.log("Spouse ID Number:", random_spouse_id_number);
}
console.log("Obligor ID:", random_obligor_id);
console.log("Bank Account:", random_bank_account);
console.log("Machine Number:", random_machine_no);
console.log("Chassis Number:", random_chassis_no);
console.log("BPKB Number:", random_bpkb_no);
console.log("Area (Price List):", random_area_pl);
console.log("Year:", random_year);
