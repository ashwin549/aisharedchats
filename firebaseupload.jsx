// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyB_DLmvXpiNJmYNArp-I5CGddmxNC4JdcQ",
  authDomain: "aisharedchats.firebaseapp.com",
  projectId: "aisharedchats",
  storageBucket: "aisharedchats.firebasestorage.app",
  messagingSenderId: "857043333029",
  appId: "1:857043333029:web:ea0f59ab5cd5cb36e0c24c",
  measurementId: "G-EG2QGGQKR8"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);