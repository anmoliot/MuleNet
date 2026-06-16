export const testIntakeRequest = {
  complaint: {
    complaintId: "COMP-101",
    utr: "UTR-98472910",
    amount: 100000.0,
    timestamp: "2023-10-01T12:00:00",
    firstBeneficiary: "AC-7739"
  },
  transactions: [
    {
      utr: "UTR-98472910",
      amount: 100000.0,
      timestamp: "2023-10-01T12:00:00",
      senderAccount: "AC-VICTIM",
      receiverAccount: "AC-7739",
      deviceId: "DEV-111"
    },
    {
      utr: "UTR-11111111",
      amount: 25000.0,
      timestamp: "2023-10-01T12:01:00",
      senderAccount: "AC-7739",
      receiverAccount: "AC-8102",
      deviceId: "DEV-111"
    },
    {
      utr: "UTR-22222222",
      amount: 25000.0,
      timestamp: "2023-10-01T12:01:10",
      senderAccount: "AC-7739",
      receiverAccount: "AC-3994",
      deviceId: "DEV-222"
    },
    {
      utr: "UTR-33333333",
      amount: 50000.0,
      timestamp: "2023-10-01T12:01:20",
      senderAccount: "AC-7739",
      receiverAccount: "AC-1199",
      deviceId: "DEV-111"
    },
    {
      utr: "UTR-44444444",
      amount: 25000.0,
      timestamp: "2023-10-01T12:05:00",
      senderAccount: "AC-8102",
      receiverAccount: "AC-1199",
      deviceId: "DEV-333"
    },
    {
      utr: "UTR-55555555",
      amount: 25000.0,
      timestamp: "2023-10-01T12:05:10",
      senderAccount: "AC-3994",
      receiverAccount: "AC-1199",
      deviceId: "DEV-444"
    }
  ]
};
