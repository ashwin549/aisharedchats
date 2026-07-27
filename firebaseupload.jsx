import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";

const firebaseConfig = {
  apiKey: "AIzaSyB_DLmvXpiNJmYNArp-I5CGddmxNC4JdcQ",
  authDomain: "aisharedchats.firebaseapp.com",
  projectId: "aisharedchats",
  storageBucket: "aisharedchats.firebasestorage.app",
  messagingSenderId: "857043333029",
  appId: "1:857043333029:web:ea0f59ab5cd5cb36e0c24c",
  measurementId: "G-EG2QGGQKR8"
};

const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
