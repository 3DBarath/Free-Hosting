// Profile Management System
const profileData = {
    user: {
        name: "John Doe",
        email: "john@healthconnect.com",
        medicalHistory: {
            bloodType: "A+",
            allergies: ["Penicillin"],
            conditions: ["Asthma"]
        },
        emergencyContacts: [
            { name: "Jane Doe", phone: "555-1234", relation: "Spouse" }
        ],
        journalEntries: []
    },

    init() {
        this.loadProfile();
        this.loadMedicalHistory();
        this.loadEmergencyContacts();
        this.loadJournalEntries();
    },

    loadProfile() {
        document.getElementById('userName').textContent = this.user.name;
        document.getElementById('userEmail').textContent = this.user.email;
    },

    loadMedicalHistory() {
        const historyHTML = Object.entries(this.user.medicalHistory)
            .map(([key, value]) => `
                <div class="history-item">
                    <strong>${key}:</strong>
                    <span>${Array.isArray(value) ? value.join(', ') : value}</span>
                </div>
            `).join('');
        document.getElementById('medicalHistory').innerHTML = historyHTML;
    },

    loadEmergencyContacts() {
        const contactsHTML = this.user.emergencyContacts.map(contact => `
            <div class="contact-item">
                <h4>${contact.name}</h4>
                <p>${contact.relation} - ${contact.phone}</p>
            </div>
        `).join('');
        document.getElementById('emergencyContacts').innerHTML = contactsHTML;
    },

    loadJournalEntries() {
        const entriesHTML = this.user.journalEntries.map(entry => `
            <div class="journal-entry">
                <small>${new Date(entry.date).toLocaleString()}</small>
                <p>${entry.content}</p>
            </div>
        `).reverse().join('');
        document.getElementById('journalEntries').innerHTML = entriesHTML;
    },

    saveJournalEntry() {
        const content = document.getElementById('journalEntry').value;
        if(content) {
            this.user.journalEntries.push({
                date: new Date(),
                content: content
            });
            this.loadJournalEntries();
            document.getElementById('journalEntry').value = '';
            showToast('Journal entry saved!', 'success');
        }
    },

    addContact() {
        const name = prompt("Enter contact name:");
        const phone = prompt("Enter phone number:");
        const relation = prompt("Enter relationship:");
        
        if(name && phone && relation) {
            this.user.emergencyContacts.push({ name, phone, relation });
            this.loadEmergencyContacts();
            showToast('Contact added!', 'success');
        }
    },

    editProfile() {
        const newName = prompt("Enter new name:", this.user.name);
        const newEmail = prompt("Enter new email:", this.user.email);
        
        if(newName) this.user.name = newName;
        if(newEmail) this.user.email = newEmail;
        
        this.loadProfile();
        showToast('Profile updated!', 'success');
    }
};

document.addEventListener('DOMContentLoaded', () => profileData.init());