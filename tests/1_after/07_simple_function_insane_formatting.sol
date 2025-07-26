// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

contract Escrow {
    function setFeeRecipient(address newRec)
        external
    {
        address oldRecipient = feeRecipient;
        emit FeeRecipientSet(oldRecipient);
    }
} 